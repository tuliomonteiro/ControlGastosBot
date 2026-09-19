import type { ExpenseWithRelations } from "@/lib/data/expenses";

export type TrendPoint = {
  period: string; // YYYY-MM
  label: string; // "Jan 2026"
  total: number;
};

export type RankedSlice = {
  label: string;
  total: number;
};

const MONTH_LABELS = [
  "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
  "Jul", "Ago", "Set", "Out", "Nov", "Dez",
];

export function aggregateByMonth(expenses: Pick<ExpenseWithRelations, "expense_date" | "amount_pyg">[]): TrendPoint[] {
  const totals = new Map<string, number>();

  for (const expense of expenses) {
    const period = expense.expense_date.slice(0, 7); // YYYY-MM
    totals.set(period, (totals.get(period) ?? 0) + expense.amount_pyg);
  }

  return Array.from(totals.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([period, total]) => {
      const [year, month] = period.split("-");
      const label = `${MONTH_LABELS[Number(month) - 1]} ${year}`;
      return { period, label, total };
    });
}

export function aggregateByCategory(
  expenses: Pick<ExpenseWithRelations, "amount_pyg" | "category">[],
  limit = 10,
): RankedSlice[] {
  return rankBy(expenses, (expense) => expense.category?.name ?? "Sem categoria", limit);
}

export function aggregateByAccount(
  expenses: Pick<ExpenseWithRelations, "amount_pyg" | "account">[],
  limit = 10,
): RankedSlice[] {
  return rankBy(expenses, (expense) => expense.account?.name ?? "Sem conta", limit);
}

function rankBy<T extends { amount_pyg: number }>(
  expenses: T[],
  keyOf: (expense: T) => string,
  limit: number,
): RankedSlice[] {
  const totals = new Map<string, number>();

  for (const expense of expenses) {
    const key = keyOf(expense);
    totals.set(key, (totals.get(key) ?? 0) + expense.amount_pyg);
  }

  const sorted = Array.from(totals.entries())
    .sort(([, a], [, b]) => b - a)
    .map(([label, total]) => ({ label, total }));

  if (sorted.length <= limit) {
    return sorted;
  }

  const head = sorted.slice(0, limit - 1);
  const tailTotal = sorted.slice(limit - 1).reduce((sum, slice) => sum + slice.total, 0);
  return [...head, { label: "Outras", total: tailTotal }];
}

export function sumAmount(expenses: Pick<ExpenseWithRelations, "amount_pyg">[]): number {
  return expenses.reduce((sum, expense) => sum + expense.amount_pyg, 0);
}

export function aggregateFacturaByMonth(
  expenses: Pick<ExpenseWithRelations, "expense_date" | "amount_pyg" | "has_invoice">[],
): RankedSlice[] {
  const withInvoice = expenses.filter((expense) => expense.has_invoice);

  // Reuses the same month buckets as the trend chart, but renders as ranked
  // horizontal bars (most recent month first) rather than a left-to-right
  // timeline, so it's reversed instead of re-sorted by magnitude.
  return aggregateByMonth(withInvoice)
    .slice()
    .reverse()
    .map(({ label, total }) => ({ label, total }));
}
