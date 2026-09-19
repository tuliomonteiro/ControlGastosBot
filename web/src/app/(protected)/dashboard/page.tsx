import { requireAllowedUser } from "@/lib/auth";
import { getHouseholdUserId } from "@/lib/household";
import {
  formatGuaraniAmount,
  listAccounts,
  listCategories,
  listExpensesInRange,
} from "@/lib/data/expenses";
import {
  aggregateByAccount,
  aggregateByCategory,
  aggregateByMonth,
  aggregateFacturaByMonth,
  sumAmount,
} from "@/lib/analytics";
import { resolveRange } from "@/lib/dashboard-filters";
import { DashboardFilters } from "@/components/dashboard/filters";
import { TrendChart } from "@/components/dashboard/trend-chart";
import { RankedBarChart } from "@/components/dashboard/ranked-bar-chart";
import styles from "@/components/dashboard/dashboard.module.css";

type DashboardPageProps = {
  searchParams: Promise<{
    range?: string;
    from?: string;
    to?: string;
    category?: string;
    account?: string;
  }>;
};

export default async function DashboardPage({ searchParams }: DashboardPageProps) {
  await requireAllowedUser("/dashboard");
  const householdUserId = getHouseholdUserId();
  const params = await searchParams;
  const range = resolveRange(params);

  const [expenses, categories, accounts] = await Promise.all([
    listExpensesInRange(householdUserId, {
      from: range.from,
      to: range.to,
      categoryId: params.category,
      accountId: params.account,
    }),
    listCategories(householdUserId),
    listAccounts(householdUserId),
  ]);

  const totalSpend = sumAmount(expenses);
  const activeCategories = new Set(expenses.map((expense) => expense.category?.id).filter(Boolean)).size;
  const trend = aggregateByMonth(expenses);
  const byCategory = aggregateByCategory(expenses);
  const byAccount = aggregateByAccount(expenses);
  const byMonthWithInvoice = aggregateFacturaByMonth(expenses);
  const totalWithInvoice = sumAmount(expenses.filter((expense) => expense.has_invoice));
  const recent = expenses.slice(-8).reverse();

  return (
    <div className={styles.root}>
      <div>
        <h1>Dashboard</h1>
        <p>Visão geral dos seus gastos, direto do Supabase.</p>
      </div>

      <DashboardFilters
        categories={categories}
        accounts={accounts}
        currentRange={range.key}
        currentFrom={params.from}
        currentTo={params.to}
        currentCategoryId={params.category}
        currentAccountId={params.account}
      />

      <div className={styles.kpiRow}>
        <div className={styles.kpiTile}>
          <span className={styles.kpiLabel}>Total de gastos</span>
          <span className={styles.kpiValue}>{expenses.length}</span>
        </div>
        <div className={styles.kpiTile}>
          <span className={styles.kpiLabel}>Total gasto</span>
          <span className={styles.kpiValue}>Gs. {formatGuaraniAmount(totalSpend)}</span>
        </div>
        <div className={styles.kpiTile}>
          <span className={styles.kpiLabel}>Média por gasto</span>
          <span className={styles.kpiValue}>
            Gs. {formatGuaraniAmount(expenses.length ? totalSpend / expenses.length : 0)}
          </span>
        </div>
        <div className={styles.kpiTile}>
          <span className={styles.kpiLabel}>Categorias ativas</span>
          <span className={styles.kpiValue}>{activeCategories}</span>
        </div>
        <div className={styles.kpiTile}>
          <span className={styles.kpiLabel}>Total com factura</span>
          <span className={styles.kpiValue}>Gs. {formatGuaraniAmount(totalWithInvoice)}</span>
        </div>
      </div>

      <div className={styles.chartGrid}>
        <div className={styles.card}>
          <div className={styles.cardTitle}>Gastos ao longo do tempo</div>
          <div className={styles.cardSubtitle}>Total mensal, no período filtrado</div>
          <TrendChart data={trend} />
        </div>

        <div className={styles.card}>
          <div className={styles.cardTitle}>Gastos por categoria</div>
          <div className={styles.cardSubtitle}>Maiores categorias no período filtrado</div>
          <RankedBarChart data={byCategory} />
        </div>

        <div className={styles.card}>
          <div className={styles.cardTitle}>Gastos por conta</div>
          <div className={styles.cardSubtitle}>Maiores contas/bancos no período filtrado</div>
          <RankedBarChart data={byAccount} />
        </div>

        <div className={styles.card}>
          <div className={styles.cardTitle}>Gastos com factura por mês</div>
          <div className={styles.cardSubtitle}>Soma mensal dos gastos com factura, no período filtrado</div>
          <RankedBarChart data={byMonthWithInvoice} />
        </div>
      </div>

      <section className={styles.card}>
        <div className={styles.cardTitle}>Gastos recentes</div>
        {recent.length === 0 ? (
          <p className={styles.emptyState}>Nenhum gasto no período selecionado.</p>
        ) : (
          <div style={{ marginTop: "12px", overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th align="left">Data</th>
                  <th align="left">Descrição</th>
                  <th align="left">Categoria</th>
                  <th align="left">Conta</th>
                  <th align="right">Valor (Gs)</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((expense) => (
                  <tr key={expense.id}>
                    <td style={{ paddingTop: "10px" }}>{expense.expense_date}</td>
                    <td style={{ paddingTop: "10px" }}>{expense.description}</td>
                    <td style={{ paddingTop: "10px" }}>{expense.category?.name ?? "Sem categoria"}</td>
                    <td style={{ paddingTop: "10px" }}>{expense.account?.name ?? "Sem conta"}</td>
                    <td align="right" style={{ paddingTop: "10px" }}>
                      {formatGuaraniAmount(expense.amount_pyg)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
