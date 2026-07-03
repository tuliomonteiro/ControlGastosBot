import { fetchExpenses } from "@/lib/sheets";
import ExpenseTable from "@/components/ExpenseTable";
import { Expense } from "@/types/expense";

export const revalidate = 300;

export default async function ExpensesPage({
  searchParams,
}: {
  searchParams: { [key: string]: string | undefined };
}) {
  let expenses: Expense[] = [];
  let error: string | null = null;

  try {
    expenses = await fetchExpenses();
  } catch (err) {
    error = err instanceof Error ? err.message : "Erro ao carregar dados";
  }

  if (error) {
    return (
      <div className="rounded-xl bg-red-50 border border-red-200 p-6 text-red-700">
        <p className="font-semibold">Erro ao conectar com Google Sheets</p>
        <p className="text-sm mt-1">{error}</p>
      </div>
    );
  }

  // Apply filters from URL params
  const { category, currency, bank, from, to, q } = searchParams;

  let filtered = expenses;
  if (category) filtered = filtered.filter((e) => e.category === category);
  if (currency) filtered = filtered.filter((e) => e.currency === currency);
  if (bank) filtered = filtered.filter((e) => e.bank === bank);
  if (from) filtered = filtered.filter((e) => e.date >= from);
  if (to) filtered = filtered.filter((e) => e.date <= to);
  if (q) {
    const lower = q.toLowerCase();
    filtered = filtered.filter(
      (e) =>
        e.description.toLowerCase().includes(lower) ||
        e.category.toLowerCase().includes(lower)
    );
  }

  filtered.sort((a, b) => b.date.localeCompare(a.date));

  // Build unique filter options from full data
  const categories = [...new Set(expenses.map((e) => e.category).filter(Boolean))].sort();
  const currencies = [...new Set(expenses.map((e) => e.currency).filter(Boolean))].sort();
  const banks = [...new Set(expenses.map((e) => e.bank).filter(Boolean))].sort();

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Historico de gastos</h1>
      <ExpenseTable
        expenses={filtered}
        categories={categories}
        currencies={currencies}
        banks={banks}
        filters={{ category, currency, bank, from, to, q }}
      />
    </div>
  );
}
