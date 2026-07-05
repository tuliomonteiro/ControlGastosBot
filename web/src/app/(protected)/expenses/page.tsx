import { requireAllowedUser } from "@/lib/auth";
import { createExpenseAction } from "@/lib/actions/expenses";
import {
  formatGuaraniAmount,
  listAccounts,
  listCategories,
  listRecentExpenses,
} from "@/lib/data/expenses";

export default async function ExpensesPage() {
  const user = await requireAllowedUser("/expenses");
  const [expenses, accounts, categories] = await Promise.all([
    listRecentExpenses(user.id, 25),
    listAccounts(user.id),
    listCategories(user.id),
  ]);

  return (
    <>
      <h1>Expenses</h1>
      <p>Recent transactions loaded from the `expenses` table.</p>

      <section style={{ marginTop: "24px" }}>
        <h2>Create expense</h2>
        {accounts.length === 0 ? (
          <p style={{ marginTop: "12px" }}>
            Create at least one account in Integrations before adding expenses.
          </p>
        ) : (
          <form action={createExpenseAction} style={{ display: "grid", gap: "12px", marginTop: "16px" }}>
            <input name="description" placeholder="Description" required />
            <div style={{ display: "grid", gap: "12px", gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
              <input name="original_amount" type="number" step="0.01" placeholder="Original amount" required />
              <input name="expense_date" type="date" required defaultValue={new Date().toISOString().slice(0, 10)} />
            </div>
            <div style={{ display: "grid", gap: "12px", gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
              <select name="currency" defaultValue="PYG">
                <option value="PYG">PYG</option>
                <option value="USD">USD</option>
                <option value="BRL">BRL</option>
                <option value="ARS">ARS</option>
              </select>
              <input name="exchange_rate" type="number" step="0.000001" defaultValue="1" />
            </div>
            <div style={{ display: "grid", gap: "12px", gridTemplateColumns: "repeat(2, minmax(0, 1fr))" }}>
              <select name="category_id" required>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
              <select name="account_id" required>
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name}
                  </option>
                ))}
              </select>
            </div>
            <select name="payment_method" defaultValue="debit_card" required>
              <option value="cash">Cash</option>
              <option value="debit_card">Debit card</option>
              <option value="credit_card">Credit card</option>
              <option value="bank_transfer">Bank transfer</option>
              <option value="qr">QR</option>
              <option value="other">Other</option>
            </select>
            <textarea name="notes" placeholder="Notes (optional)" rows={3} />
            <label style={{ display: "flex", gap: "8px", alignItems: "center" }}>
              <input name="has_invoice" type="checkbox" />
              Invoice generated
            </label>
            <button type="submit" style={{ width: "fit-content", border: 0, borderRadius: "999px", background: "#1d221c", color: "#fff", padding: "12px 18px", fontWeight: 700, cursor: "pointer" }}>
              Save expense
            </button>
          </form>
        )}
      </section>

      {expenses.length === 0 ? (
        <p style={{ marginTop: "24px" }}>
          No expenses found yet. Once Telegram ingestion or manual creation is wired,
          they will appear here.
        </p>
      ) : (
        <div style={{ marginTop: "24px", overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th align="left">Date</th>
                <th align="left">Description</th>
                <th align="left">Category</th>
                <th align="left">Account</th>
                <th align="left">Method</th>
                <th align="left">Invoice</th>
                <th align="right">Amount (PYG)</th>
              </tr>
            </thead>
            <tbody>
              {expenses.map((expense) => (
                <tr key={expense.id}>
                  <td style={{ paddingTop: "10px" }}>{expense.expense_date}</td>
                  <td style={{ paddingTop: "10px" }}>{expense.description}</td>
                  <td style={{ paddingTop: "10px" }}>
                    {expense.category?.name ?? "No category"}
                  </td>
                  <td style={{ paddingTop: "10px" }}>
                    {expense.account?.name ?? "No account"}
                  </td>
                  <td style={{ paddingTop: "10px" }}>{expense.payment_method}</td>
                  <td style={{ paddingTop: "10px" }}>
                    {expense.has_invoice ? "Yes" : "No"}
                  </td>
                  <td align="right" style={{ paddingTop: "10px" }}>
                    Gs. {formatGuaraniAmount(expense.amount_pyg)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
