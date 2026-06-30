import { fetchExpenses } from "@/lib/sheets";
import Card from "@/components/ui/Card";
import MonthlyChart from "@/components/charts/MonthlyChart";
import CategoryChart from "@/components/charts/CategoryChart";
import CurrencyChart from "@/components/charts/CurrencyChart";
import { format, parseISO, isValid } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  Expense,
  MonthlySummary,
  CategorySummary,
  CurrencySummary,
} from "@/types/expense";

export const revalidate = 300;

function formatGs(value: number) {
  return new Intl.NumberFormat("es-PY").format(Math.round(value));
}

function buildStats(expenses: Expense[]) {
  const now = new Date();
  const thisMonthKey = format(now, "yyyy-MM");

  const thisMonth = expenses.filter((e) => e.date.startsWith(thisMonthKey));

  const monthMap = new Map<string, MonthlySummary>();
  for (let i = 5; i >= 0; i--) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const key = format(d, "yyyy-MM");
    monthMap.set(key, {
      month: format(d, "MMM yyyy", { locale: ptBR }),
      totalGs: 0,
      count: 0,
    });
  }

  for (const e of expenses) {
    const key = e.date.slice(0, 7);
    if (monthMap.has(key)) {
      const m = monthMap.get(key)!;
      m.totalGs += e.amountGs;
      m.count += 1;
    }
  }

  const catMap = new Map<string, CategorySummary>();
  for (const e of expenses) {
    const cat = e.category || "OUTRA";
    const existing = catMap.get(cat) ?? { category: cat, totalGs: 0, count: 0 };
    existing.totalGs += e.amountGs;
    existing.count += 1;
    catMap.set(cat, existing);
  }

  const currMap = new Map<string, CurrencySummary>();
  for (const e of expenses) {
    const cur = e.currency || "?";
    const existing = currMap.get(cur) ?? {
      currency: cur,
      totalGs: 0,
      count: 0,
    };
    existing.totalGs += e.amountGs;
    existing.count += 1;
    currMap.set(cur, existing);
  }

  const byCategory = [...catMap.values()]
    .sort((a, b) => b.totalGs - a.totalGs)
    .slice(0, 10);
  const byCurrency = [...currMap.values()].sort(
    (a, b) => b.totalGs - a.totalGs
  );

  return {
    totalThisMonth: thisMonth.reduce((s, e) => s + e.amountGs, 0),
    totalThisMonthCount: thisMonth.length,
    topCategory: byCategory[0]?.category ?? "-",
    monthly: [...monthMap.values()],
    byCategory,
    byCurrency,
  };
}

export default async function DashboardPage() {
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
        <p className="text-xs mt-3 text-red-500">
          Verifique as variáveis de ambiente: GOOGLE_SERVICE_ACCOUNT_EMAIL,
          GOOGLE_PRIVATE_KEY, GOOGLE_SPREADSHEET_ID
        </p>
      </div>
    );
  }

  const stats = buildStats(expenses);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card
          title="Gasto este mes"
          value={`Gs ${formatGs(stats.totalThisMonth)}`}
          subtitle={`${stats.totalThisMonthCount} transacoes`}
        />
        <Card
          title="Total de registros"
          value={expenses.length.toString()}
          subtitle="todos os periodos"
        />
        <Card
          title="Categoria principal"
          value={stats.topCategory}
          subtitle="maior gasto acumulado"
        />
        <Card
          title="Moeda principal"
          value={stats.byCurrency[0]?.currency ?? "-"}
          subtitle="maior volume em Gs"
        />
      </div>

      {/* Monthly bar chart */}
      <MonthlyChart data={stats.monthly} />

      {/* Category + Currency side by side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <CategoryChart data={stats.byCategory} />
        <CurrencyChart data={stats.byCurrency} />
      </div>
    </div>
  );
}
