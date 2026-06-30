import { NextResponse } from "next/server";
import { fetchExpenses } from "@/lib/sheets";
import { Expense, DashboardStats, MonthlySummary, CategorySummary, CurrencySummary } from "@/types/expense";
import { format, parseISO, startOfMonth, isValid } from "date-fns";

export const revalidate = 300; // cache for 5 minutes

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const view = searchParams.get("view");

  try {
    const expenses = await fetchExpenses();

    if (view === "stats") {
      return NextResponse.json(buildStats(expenses));
    }

    // Optional filters for the history table
    const category = searchParams.get("category");
    const currency = searchParams.get("currency");
    const bank = searchParams.get("bank");
    const from = searchParams.get("from");
    const to = searchParams.get("to");

    let filtered = expenses;
    if (category) filtered = filtered.filter((e) => e.category === category);
    if (currency) filtered = filtered.filter((e) => e.currency === currency);
    if (bank) filtered = filtered.filter((e) => e.bank === bank);
    if (from) filtered = filtered.filter((e) => e.date >= from);
    if (to) filtered = filtered.filter((e) => e.date <= to);

    // Sort newest first
    filtered.sort((a, b) => b.date.localeCompare(a.date));

    return NextResponse.json(filtered);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

function buildStats(expenses: Expense[]): DashboardStats {
  const now = new Date();
  const thisMonthKey = format(now, "yyyy-MM");

  const thisMonth = expenses.filter(
    (e) => e.date.startsWith(thisMonthKey) && isValid(parseISO(e.date))
  );

  // Monthly totals for last 6 months
  const monthMap = new Map<string, MonthlySummary>();
  for (let i = 5; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const key = format(d, "yyyy-MM");
    monthMap.set(key, { month: format(d, "MMM yyyy"), totalGs: 0, count: 0 });
  }

  for (const e of expenses) {
    if (!isValid(parseISO(e.date))) continue;
    const key = e.date.slice(0, 7);
    if (monthMap.has(key)) {
      const m = monthMap.get(key)!;
      m.totalGs += e.amountGs;
      m.count += 1;
    }
  }

  // By category
  const catMap = new Map<string, CategorySummary>();
  for (const e of expenses) {
    const cat = e.category || "OUTRA";
    const existing = catMap.get(cat) ?? { category: cat, totalGs: 0, count: 0 };
    existing.totalGs += e.amountGs;
    existing.count += 1;
    catMap.set(cat, existing);
  }

  // By currency
  const currMap = new Map<string, CurrencySummary>();
  for (const e of expenses) {
    const cur = e.currency || "?";
    const existing = currMap.get(cur) ?? { currency: cur, totalGs: 0, count: 0 };
    existing.totalGs += e.amountGs;
    existing.count += 1;
    currMap.set(cur, existing);
  }

  const byCategory = [...catMap.values()].sort((a, b) => b.totalGs - a.totalGs);
  const byCurrency = [...currMap.values()].sort((a, b) => b.totalGs - a.totalGs);

  return {
    totalThisMonth: thisMonth.reduce((s, e) => s + e.amountGs, 0),
    totalThisMonthCount: thisMonth.length,
    topCategory: byCategory[0]?.category ?? "-",
    topCurrency: byCurrency[0]?.currency ?? "-",
    monthly: [...monthMap.values()],
    byCategory: byCategory.slice(0, 10),
    byCurrency,
  };
}
