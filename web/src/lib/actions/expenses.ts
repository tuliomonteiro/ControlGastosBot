"use server";

import { revalidatePath } from "next/cache";
import { requireAllowedUser } from "@/lib/auth";
import {
  createAccount,
  createCategory,
  createExpense,
  type PaymentMethod,
  upsertTelegramConnection,
} from "@/lib/data/expenses";

function getString(formData: FormData, key: string) {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function getBoolean(formData: FormData, key: string) {
  return formData.get(key) === "on";
}

function isPaymentMethod(value: string): value is PaymentMethod {
  return [
    "cash",
    "debit_card",
    "credit_card",
    "bank_transfer",
    "qr",
    "other",
  ].includes(value);
}

export async function createAccountAction(formData: FormData) {
  const user = await requireAllowedUser("/settings/integrations");
  const name = getString(formData, "name");

  if (!name) {
    throw new Error("Account name is required.");
  }

  await createAccount(user.id, name);
  revalidatePath("/settings/integrations");
  revalidatePath("/dashboard");
  revalidatePath("/expenses");
}

export async function createCategoryAction(formData: FormData) {
  const user = await requireAllowedUser("/settings/integrations");
  const name = getString(formData, "name");

  if (!name) {
    throw new Error("Category name is required.");
  }

  await createCategory(user.id, name);
  revalidatePath("/settings/integrations");
  revalidatePath("/dashboard");
  revalidatePath("/expenses");
}

export async function createExpenseAction(formData: FormData) {
  const user = await requireAllowedUser("/expenses");
  const description = getString(formData, "description");
  const originalAmount = Number(getString(formData, "original_amount"));
  const currency = (getString(formData, "currency") || "PYG").toUpperCase();
  const exchangeRateInput = getString(formData, "exchange_rate");
  const exchangeRate = exchangeRateInput ? Number(exchangeRateInput) : 1;
  const expenseDate = getString(formData, "expense_date");
  const categoryId = getString(formData, "category_id");
  const accountId = getString(formData, "account_id");
  const paymentMethod = getString(formData, "payment_method");
  const notes = getString(formData, "notes") || null;
  const hasInvoice = getBoolean(formData, "has_invoice");

  if (!description || !categoryId || !accountId || !expenseDate || !paymentMethod) {
    throw new Error("Missing required expense fields.");
  }

  if (!isPaymentMethod(paymentMethod)) {
    throw new Error("Invalid payment method.");
  }

  if (!Number.isFinite(originalAmount) || originalAmount <= 0) {
    throw new Error("Original amount must be a positive number.");
  }

  if (!Number.isFinite(exchangeRate) || exchangeRate <= 0) {
    throw new Error("Exchange rate must be a positive number.");
  }

  const amountPyg = currency === "PYG" ? originalAmount : originalAmount * exchangeRate;

  await createExpense({
    userId: user.id,
    description,
    originalAmount,
    currency,
    exchangeRate,
    amountPyg,
    expenseDate,
    categoryId,
    accountId,
    paymentMethod,
    hasInvoice,
    notes,
    source: "manual",
  });

  revalidatePath("/dashboard");
  revalidatePath("/expenses");
}

export async function saveTelegramConnectionAction(formData: FormData) {
  const user = await requireAllowedUser("/settings/integrations");
  const telegramChatId = getString(formData, "telegram_chat_id");
  const telegramUserId = getString(formData, "telegram_user_id") || null;

  if (!telegramChatId) {
    throw new Error("Telegram chat ID is required.");
  }

  await upsertTelegramConnection(user.id, telegramChatId, telegramUserId);
  revalidatePath("/settings/integrations");
  revalidatePath("/dashboard");
}
