import { NextResponse } from "next/server";
import {
  createExpense,
  resolveAccountId,
  resolveCategoryIdBySlug,
} from "@/lib/data/expenses";
import { createServiceRoleClient } from "@/lib/supabase/service-role";
import { inferCategorySlug } from "@/lib/telegram/categories";
import type { AppSupabaseClient } from "@/lib/supabase/types";

type TelegramMessagePayload = {
  message?: {
    message_id?: number;
    text?: string;
    date?: number;
    chat?: {
      id?: number | string;
    };
  };
  expense?: {
    description: string;
    original_amount: number;
    currency?: string;
    exchange_rate?: number;
    expense_date?: string;
    account?: string;
    payment_method?: "cash" | "debit_card" | "credit_card" | "bank_transfer" | "qr" | "other";
    has_invoice?: boolean;
    category_slug?: string;
    notes?: string;
    external_source_id?: string;
    telegram_chat_id?: string | number;
  };
};

type NormalizedWebhookExpense = {
  description: string;
  original_amount: number;
  currency: string;
  exchange_rate: number;
  expense_date?: string;
  account: string;
  payment_method: "cash" | "debit_card" | "credit_card" | "bank_transfer" | "qr" | "other";
  has_invoice: boolean;
  category_slug?: string;
  notes?: string | null;
  external_source_id?: string;
};

function parseDateFromUnix(timestamp?: number) {
  if (!timestamp) {
    return new Date().toISOString().slice(0, 10);
  }

  return new Date(timestamp * 1000).toISOString().slice(0, 10);
}

function parseLegacyExpenseText(text: string) {
  const parts = text.split(";").map((part) => part.trim()).filter(Boolean);

  if (parts.length < 5) {
    return null;
  }

  if (parts.length === 5) {
    const [description, amount, account, paymentMethod, invoice] = parts;
    return {
      description,
      originalAmount: Number(amount.replace(/\./g, "").replace(",", ".")),
      currency: "PYG",
      exchangeRate: 1,
      account,
      paymentMethod,
      hasInvoice: /^(si|yes|true|1)$/i.test(invoice),
    };
  }

  const [description, currency, amount, exchangeRate, account, paymentMethod, invoice] = parts;
  return {
    description,
    originalAmount: Number(amount.replace(/\./g, "").replace(",", ".")),
    currency: currency.toUpperCase() === "GS" ? "PYG" : currency.toUpperCase(),
    exchangeRate: Number(exchangeRate.replace(/\./g, "").replace(",", ".")),
    account,
    paymentMethod,
    hasInvoice: /^(si|yes|true|1)$/i.test(invoice),
  };
}

function isAuthorizedRequest(request: Request) {
  const expectedSecret = process.env.TELEGRAM_WEBHOOK_SECRET;

  if (!expectedSecret) {
    return false;
  }

  const providedSecret = request.headers.get("x-telegram-bot-api-secret-token");
  return providedSecret === expectedSecret;
}

async function resolveTelegramUserId(
  telegramChatId: string,
  supabase: AppSupabaseClient,
) {
  const { data, error } = await supabase
    .from("telegram_connections")
    .select("user_id")
    .eq("telegram_chat_id", telegramChatId)
    .eq("is_active", true)
    .maybeSingle();

  if (error) {
    throw new Error(`Failed to resolve Telegram connection: ${error.message}`);
  }

  if (!data) {
    throw new Error(`Telegram chat ${telegramChatId} is not linked to any user.`);
  }

  return data.user_id;
}

export async function POST(request: Request) {
  if (!isAuthorizedRequest(request)) {
    return NextResponse.json({ ok: false, error: "Unauthorized." }, { status: 401 });
  }

  const payload = (await request.json().catch(() => null)) as TelegramMessagePayload | null;

  if (!payload) {
    return NextResponse.json({ ok: false, error: "Invalid JSON body." }, { status: 400 });
  }

  const supabase = createServiceRoleClient();

  try {
    const explicitExpense = payload.expense;
    const message = payload.message;

    if (!explicitExpense && !message?.text) {
      return NextResponse.json(
        { ok: false, error: "No supported expense payload found." },
        { status: 422 },
      );
    }

    const telegramChatId = String(
      explicitExpense?.telegram_chat_id ?? message?.chat?.id ?? "",
    ).trim();

    if (!telegramChatId) {
      return NextResponse.json(
        { ok: false, error: "telegram_chat_id is required." },
        { status: 422 },
      );
    }

    const userId = await resolveTelegramUserId(telegramChatId, supabase);

    const parsed: NormalizedWebhookExpense | null =
      explicitExpense
        ? {
            description: explicitExpense.description,
            original_amount: explicitExpense.original_amount,
            currency: (explicitExpense.currency ?? "PYG").toUpperCase(),
            exchange_rate: explicitExpense.exchange_rate ?? 1,
            expense_date: explicitExpense.expense_date,
            account: explicitExpense.account ?? "",
            payment_method: explicitExpense.payment_method ?? "other",
            has_invoice: explicitExpense.has_invoice ?? false,
            category_slug: explicitExpense.category_slug,
            notes: explicitExpense.notes ?? null,
            external_source_id: explicitExpense.external_source_id,
          }
        : (() => {
        const legacy = parseLegacyExpenseText(message?.text ?? "");
        if (!legacy) {
          return null;
        }

        return {
          description: legacy.description,
          original_amount: legacy.originalAmount,
          currency: legacy.currency,
          exchange_rate: legacy.exchangeRate,
          expense_date: parseDateFromUnix(message?.date),
          account: legacy.account,
          payment_method:
            legacy.paymentMethod.toLowerCase() === "credito"
              ? "credit_card"
              : legacy.paymentMethod.toLowerCase() === "debito"
                ? "debit_card"
                : "other",
          has_invoice: legacy.hasInvoice,
          category_slug: inferCategorySlug(legacy.description),
          notes: null,
          external_source_id: message?.message_id ? String(message.message_id) : undefined,
        };
      })();

    if (!parsed) {
      return NextResponse.json(
        { ok: false, error: "Unsupported Telegram message format." },
        { status: 422 },
      );
    }

    if (!parsed.account) {
      return NextResponse.json(
        { ok: false, error: "Account is required for Telegram expenses." },
        { status: 422 },
      );
    }

    const currency = (parsed.currency ?? "PYG").toUpperCase();
    const exchangeRate = parsed.exchange_rate ?? 1;
    const categorySlug = parsed.category_slug ?? inferCategorySlug(parsed.description);
    const [accountId, categoryId] = await Promise.all([
      resolveAccountId(userId, parsed.account, supabase),
      resolveCategoryIdBySlug(userId, categorySlug, supabase),
    ]);

    const created = await createExpense(
      {
        userId,
        description: parsed.description,
        originalAmount: parsed.original_amount,
        currency,
        exchangeRate,
        amountPyg:
          currency === "PYG"
            ? parsed.original_amount
            : parsed.original_amount * exchangeRate,
        expenseDate: parsed.expense_date ?? parseDateFromUnix(message?.date),
        categoryId,
        accountId,
        paymentMethod: parsed.payment_method ?? "other",
        hasInvoice: parsed.has_invoice ?? false,
        notes: parsed.notes ?? null,
        source: "telegram",
        sourceText: message?.text ?? null,
        sourcePayload: payload,
        externalSourceId:
          parsed.external_source_id ??
          (message?.message_id ? String(message.message_id) : null),
      },
      supabase,
    );

    return NextResponse.json({ ok: true, expenseId: created.id });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown webhook error.";
    return NextResponse.json({ ok: false, error: message }, { status: 422 });
  }
}
