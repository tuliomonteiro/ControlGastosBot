import { requireAllowedUser } from "@/lib/auth";
import {
  createAccountAction,
  createCategoryAction,
  saveTelegramConnectionAction,
} from "@/lib/actions/expenses";
import {
  listAccounts,
  listCategories,
  listTelegramConnections,
} from "@/lib/data/expenses";

export default async function IntegrationsPage() {
  const user = await requireAllowedUser("/settings/integrations");
  const [accounts, categories, telegramConnections] = await Promise.all([
    listAccounts(user.id),
    listCategories(user.id),
    listTelegramConnections(user.id),
  ]);

  return (
    <>
      <h1>Integrations</h1>
      <p>
        Current integration-related data from the database.
      </p>

      <div style={{ display: "grid", gap: "12px", marginTop: "24px" }}>
        <div>
          <strong>Accounts configured:</strong> {accounts.length}
        </div>
        <div>
          <strong>Categories available:</strong> {categories.length}
        </div>
        <div>
          <strong>Telegram connections:</strong> {telegramConnections.length}
        </div>
      </div>

      <section style={{ marginTop: "28px" }}>
        <h2>Add account</h2>
        <form action={createAccountAction} style={{ display: "flex", gap: "12px", marginTop: "12px", flexWrap: "wrap" }}>
          <input name="name" placeholder="Ueno, Continental, Cash..." required />
          <button type="submit" style={{ border: 0, borderRadius: "999px", background: "#1d221c", color: "#fff", padding: "10px 16px", fontWeight: 700, cursor: "pointer" }}>
            Create account
          </button>
        </form>
      </section>

      <section style={{ marginTop: "28px" }}>
        <h2>Add custom category</h2>
        <form action={createCategoryAction} style={{ display: "flex", gap: "12px", marginTop: "12px", flexWrap: "wrap" }}>
          <input name="name" placeholder="Custom category name" required />
          <button type="submit" style={{ border: 0, borderRadius: "999px", background: "#1d221c", color: "#fff", padding: "10px 16px", fontWeight: 700, cursor: "pointer" }}>
            Create category
          </button>
        </form>
      </section>

      <section style={{ marginTop: "28px" }}>
        <h2>Link Telegram chat</h2>
        <p style={{ marginTop: "12px" }}>
          Add the Telegram chat ID that will be allowed to send expenses into your
          account. The webhook resolves ownership from this mapping.
        </p>
        <form action={saveTelegramConnectionAction} style={{ display: "grid", gap: "12px", marginTop: "12px", maxWidth: "480px" }}>
          <input
            name="telegram_chat_id"
            placeholder="Telegram chat ID"
            required
          />
          <input
            name="telegram_user_id"
            placeholder="Telegram user ID (optional)"
          />
          <button type="submit" style={{ width: "fit-content", border: 0, borderRadius: "999px", background: "#1d221c", color: "#fff", padding: "10px 16px", fontWeight: 700, cursor: "pointer" }}>
            Save Telegram connection
          </button>
        </form>
      </section>

      <section style={{ marginTop: "28px" }}>
        <h2>Current accounts</h2>
        <ul style={{ marginTop: "12px", paddingLeft: "20px" }}>
          {accounts.length === 0 ? <li>No accounts yet.</li> : accounts.map((account) => <li key={account.id}>{account.name}</li>)}
        </ul>
      </section>

      <section style={{ marginTop: "28px" }}>
        <h2>Current categories</h2>
        <ul style={{ marginTop: "12px", paddingLeft: "20px" }}>
          {categories.slice(0, 20).map((category) => (
            <li key={category.id}>
              {category.name}
              {category.user_id ? " (custom)" : " (default)"}
            </li>
          ))}
        </ul>
      </section>

      <section style={{ marginTop: "28px" }}>
        <h2>Current Telegram connections</h2>
        <ul style={{ marginTop: "12px", paddingLeft: "20px" }}>
          {telegramConnections.length === 0 ? (
            <li>No Telegram chats linked yet.</li>
          ) : (
            telegramConnections.map((connection) => (
              <li key={connection.id}>
                chat_id: {connection.telegram_chat_id}
                {connection.telegram_user_id
                  ? ` | user_id: ${connection.telegram_user_id}`
                  : ""}
                {connection.is_active ? " | active" : " | inactive"}
              </li>
            ))
          )}
        </ul>
      </section>
    </>
  );
}
