import type { Tables } from "@/lib/database.types";
import { createClient } from "@/lib/supabase/server";
import type { AppSupabaseClient } from "@/lib/supabase/types";
import { slugify } from "@/lib/slug";

export type Category = Tables<"categories">;
export type Account = Tables<"accounts">;
export type Expense = Tables<"expenses">;
export type TelegramConnection = Tables<"telegram_connections">;
export type PaymentMethod = Expense["payment_method"];
export type ExpenseSource = Expense["source"];

export type ExpenseWithRelations = Expense & {
  account: Pick<Account, "id" | "name" | "slug"> | null;
  category: Pick<Category, "id" | "name" | "slug"> | null;
};

async function getServerClient() {
  return createClient();
}

export async function listCategories(userId: string) {
  const supabase = await getServerClient();
  const { data, error } = await supabase
    .from("categories")
    .select("id, name, slug, is_active, user_id, created_at, updated_at")
    .or(`user_id.is.null,user_id.eq.${userId}`)
    .order("name");

  if (error) {
    throw new Error(`Failed to load categories: ${error.message}`);
  }

  return data satisfies Category[];
}

export async function resolveCategoryIdBySlug(
  userId: string,
  slug: string,
  client?: AppSupabaseClient,
) {
  const supabase = client ?? (await getServerClient());
  const { data, error } = await supabase
    .from("categories")
    .select("id")
    .or(`user_id.is.null,user_id.eq.${userId}`)
    .eq("slug", slug)
    .limit(1)
    .maybeSingle();

  if (error) {
    throw new Error(`Failed to resolve category: ${error.message}`);
  }

  if (!data) {
    throw new Error(`Category with slug "${slug}" was not found.`);
  }

  return data.id;
}

export async function listAccounts(userId: string) {
  const supabase = await getServerClient();
  const { data, error } = await supabase
    .from("accounts")
    .select("id, name, slug, is_active, user_id, created_at, updated_at")
    .eq("user_id", userId)
    .order("name");

  if (error) {
    throw new Error(`Failed to load accounts: ${error.message}`);
  }

  return data satisfies Account[];
}

export async function resolveAccountId(
  userId: string,
  identifier: string,
  client?: AppSupabaseClient,
) {
  const trimmed = identifier.trim();
  const supabase = client ?? (await getServerClient());

  const { data: bySlug, error: slugError } = await supabase
    .from("accounts")
    .select("id")
    .eq("user_id", userId)
    .eq("slug", slugify(trimmed.toLowerCase()))
    .maybeSingle();

  if (slugError) {
    throw new Error(`Failed to resolve account: ${slugError.message}`);
  }

  if (bySlug) {
    return bySlug.id;
  }

  const { data: byName, error: nameError } = await supabase
    .from("accounts")
    .select("id")
    .eq("user_id", userId)
    .ilike("name", trimmed)
    .limit(1)
    .maybeSingle();

  if (nameError) {
    throw new Error(`Failed to resolve account: ${nameError.message}`);
  }

  if (!byName) {
    throw new Error(`Account "${identifier}" was not found.`);
  }

  return byName.id;
}

export async function listRecentExpenses(userId: string, limit = 10) {
  const supabase = await getServerClient();
  const { data, error } = await supabase
    .from("expenses")
    .select(
      `
        id,
        user_id,
        description,
        original_amount,
        currency,
        exchange_rate,
        amount_pyg,
        expense_date,
        category_id,
        account_id,
        payment_method,
        has_invoice,
        source,
        source_text,
        source_payload,
        external_source_id,
        notes,
        created_at,
        updated_at,
        account:accounts(id, name, slug),
        category:categories(id, name, slug)
      `,
    )
    .eq("user_id", userId)
    .order("expense_date", { ascending: false })
    .order("created_at", { ascending: false })
    .limit(limit);

  if (error) {
    throw new Error(`Failed to load expenses: ${error.message}`);
  }

  return data as ExpenseWithRelations[];
}

export async function createAccount(userId: string, name: string) {
  const supabase = await getServerClient();
  const { data, error } = await supabase
    .from("accounts")
    .insert({
      user_id: userId,
      name,
      slug: slugify(name),
    })
    .select()
    .single();

  if (error) {
    throw new Error(`Failed to create account: ${error.message}`);
  }

  return data satisfies Account;
}

export async function createCategory(userId: string, name: string) {
  const supabase = await getServerClient();
  const { data, error } = await supabase
    .from("categories")
    .insert({
      user_id: userId,
      name,
      slug: slugify(name),
    })
    .select()
    .single();

  if (error) {
    throw new Error(`Failed to create category: ${error.message}`);
  }

  return data satisfies Category;
}

type CreateExpenseInput = {
  userId: string;
  description: string;
  originalAmount: number;
  currency: string;
  exchangeRate: number;
  amountPyg: number;
  expenseDate: string;
  categoryId: string;
  accountId: string;
  paymentMethod: PaymentMethod;
  hasInvoice: boolean;
  notes?: string | null;
  source?: ExpenseSource;
  sourceText?: string | null;
  sourcePayload?: Expense["source_payload"];
  externalSourceId?: string | null;
};

export async function createExpense(
  input: CreateExpenseInput,
  client?: AppSupabaseClient,
) {
  const supabase = client ?? (await getServerClient());
  const { data, error } = await supabase
    .from("expenses")
    .insert({
      user_id: input.userId,
      description: input.description,
      original_amount: input.originalAmount,
      currency: input.currency,
      exchange_rate: input.exchangeRate,
      amount_pyg: input.amountPyg,
      expense_date: input.expenseDate,
      category_id: input.categoryId,
      account_id: input.accountId,
      payment_method: input.paymentMethod,
      has_invoice: input.hasInvoice,
      notes: input.notes ?? null,
      source: input.source ?? "manual",
      source_text: input.sourceText ?? null,
      source_payload: input.sourcePayload ?? null,
      external_source_id: input.externalSourceId ?? null,
    })
    .select()
    .single();

  if (error) {
    throw new Error(`Failed to create expense: ${error.message}`);
  }

  return data satisfies Expense;
}

export async function listTelegramConnections(userId: string) {
  const supabase = await getServerClient();
  const { data, error } = await supabase
    .from("telegram_connections")
    .select(
      "id, user_id, telegram_chat_id, telegram_user_id, is_active, created_at, updated_at",
    )
    .eq("user_id", userId)
    .order("created_at", { ascending: false });

  if (error) {
    throw new Error(`Failed to load Telegram connections: ${error.message}`);
  }

  return data satisfies TelegramConnection[];
}

export async function upsertTelegramConnection(
  userId: string,
  telegramChatId: string,
  telegramUserId?: string | null,
) {
  const supabase = await getServerClient();
  const { data, error } = await supabase
    .from("telegram_connections")
    .upsert(
      {
        user_id: userId,
        telegram_chat_id: telegramChatId,
        telegram_user_id: telegramUserId ?? null,
        is_active: true,
      },
      {
        onConflict: "telegram_chat_id",
      },
    )
    .select()
    .single();

  if (error) {
    throw new Error(`Failed to save Telegram connection: ${error.message}`);
  }

  return data satisfies TelegramConnection;
}

export async function getExpenseCount(userId: string) {
  const supabase = await getServerClient();
  const { count, error } = await supabase
    .from("expenses")
    .select("id", { count: "exact", head: true })
    .eq("user_id", userId);

  if (error) {
    throw new Error(`Failed to count expenses: ${error.message}`);
  }

  return count ?? 0;
}

export async function getCurrentMonthSpendPyg(userId: string) {
  const now = new Date();
  const monthStart = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1))
    .toISOString()
    .slice(0, 10);

  const supabase = await getServerClient();
  const { data, error } = await supabase
    .from("expenses")
    .select("amount_pyg")
    .eq("user_id", userId)
    .gte("expense_date", monthStart);

  if (error) {
    throw new Error(`Failed to load monthly spend: ${error.message}`);
  }

  return data.reduce((sum, expense) => sum + expense.amount_pyg, 0);
}

export async function getDashboardSnapshot(userId: string) {
  const [
    expenseCount,
    monthSpendPyg,
    recentExpenses,
    accounts,
    categories,
    telegramConnections,
  ] =
    await Promise.all([
      getExpenseCount(userId),
      getCurrentMonthSpendPyg(userId),
      listRecentExpenses(userId, 5),
      listAccounts(userId),
      listCategories(userId),
      listTelegramConnections(userId),
    ]);

  return {
    expenseCount,
    monthSpendPyg,
    recentExpenses,
    accounts,
    categories,
    telegramConnections,
  };
}

export function formatGuaraniAmount(value: number) {
  return new Intl.NumberFormat("es-PY", {
    maximumFractionDigits: 0,
  }).format(value);
}
