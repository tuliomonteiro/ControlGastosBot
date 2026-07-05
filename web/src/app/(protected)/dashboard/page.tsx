import { requireAllowedUser } from "@/lib/auth";
import {
  formatGuaraniAmount,
  getDashboardSnapshot,
} from "@/lib/data/expenses";

export default async function DashboardPage() {
  const user = await requireAllowedUser("/dashboard");
  const snapshot = await getDashboardSnapshot(user.id);

  return (
    <>
      <h1>Dashboard</h1>
      <p>Authenticated overview backed by Supabase.</p>

      <div style={{ display: "grid", gap: "12px", marginTop: "24px" }}>
        <div>
          <strong>Total expenses:</strong> {snapshot.expenseCount}
        </div>
        <div>
          <strong>Current month spend:</strong> Gs.{" "}
          {formatGuaraniAmount(snapshot.monthSpendPyg)}
        </div>
        <div>
          <strong>Accounts configured:</strong> {snapshot.accounts.length}
        </div>
        <div>
          <strong>Categories available:</strong> {snapshot.categories.length}
        </div>
      </div>

      <section style={{ marginTop: "32px" }}>
        <h2>Recent expenses</h2>
        {snapshot.recentExpenses.length === 0 ? (
          <p>No expenses yet. The database connection is working, but there is no data.</p>
        ) : (
          <ul style={{ marginTop: "16px", paddingLeft: "20px" }}>
            {snapshot.recentExpenses.map((expense) => (
              <li key={expense.id} style={{ marginBottom: "10px" }}>
                {expense.description} | Gs. {formatGuaraniAmount(expense.amount_pyg)} |{" "}
                {expense.category?.name ?? "No category"} |{" "}
                {expense.account?.name ?? "No account"} | {expense.expense_date}
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
