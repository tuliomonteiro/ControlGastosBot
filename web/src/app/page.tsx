import Link from "next/link";
import { getCurrentUser, isEmailAllowed } from "@/lib/auth";
import styles from "./page.module.css";

const appRoutes = [
  {
    href: "/login",
    title: "Login",
    description: "Authentication entry point for the new web app.",
  },
  {
    href: "/dashboard",
    title: "Dashboard",
    description: "Summary cards and reporting will live here.",
  },
  {
    href: "/expenses",
    title: "Expenses",
    description: "List, filter, and review transactions from Postgres.",
  },
  {
    href: "/settings/integrations",
    title: "Integrations",
    description: "Telegram, Supabase, and Google Sheets configuration.",
  },
];

const apiRoutes = [
  "/api/telegram/webhook",
  "/api/cron/sync-google-sheets",
];

export default async function Home() {
  const user = await getCurrentUser();
  const isAllowedUser = isEmailAllowed(user?.email);

  return (
    <div className={styles.page}>
      <main className={styles.shell}>
        <section className={styles.hero}>
          <p className={styles.eyebrow}>ControlGastos Web</p>
          <h1>Separate Next.js app for the Vercel + Supabase migration.</h1>
          <p className={styles.copy}>
            This starter mirrors the migration plan in the bot repository:
            Postgres as source of truth, Telegram webhook ingestion, dashboard
            routes, and a daily Google Sheets sync job.
          </p>
        </section>

        <section className={styles.grid}>
          {appRoutes.map((route) => (
            <Link key={route.href} href={route.href} className={styles.card}>
              <span>{route.title}</span>
              <p>{route.description}</p>
            </Link>
          ))}
        </section>

        <section className={styles.panel}>
          <h2>{isAllowedUser ? "Authenticated session found" : "Authentication status"}</h2>
          <p className={styles.panelCopy}>
            {isAllowedUser
              ? `Signed in as ${user?.email}. Continue into the protected workspace.`
              : "No approved user is signed in yet. Finish the Google + Supabase setup, then sign in."}
          </p>
          <div className={styles.panelActions}>
            <Link href={isAllowedUser ? "/dashboard" : "/login"}>
              {isAllowedUser ? "Open Dashboard" : "Go To Login"}
            </Link>
          </div>
        </section>

        <section className={styles.panel}>
          <h2>API placeholders</h2>
          <ul className={styles.apiList}>
            {apiRoutes.map((route) => (
              <li key={route}>
                <code>{route}</code>
              </li>
            ))}
          </ul>
        </section>
      </main>
    </div>
  );
}
