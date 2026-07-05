import Link from "next/link";
import { SignOutButton } from "@/components/auth/sign-out-button";
import { requireAllowedUser } from "@/lib/auth";
import styles from "./protected.module.css";

const navigation = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/expenses", label: "Expenses" },
  { href: "/settings/integrations", label: "Integrations" },
];

export default async function ProtectedLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const user = await requireAllowedUser("/dashboard");

  return (
    <div className={styles.shell}>
      <div className={styles.frame}>
        <header className={styles.header}>
          <div className={styles.brand}>
            <p>ControlGastos Web</p>
            <h1>Authenticated Workspace</h1>
          </div>

          <div className={styles.meta}>
            <span>{user.email}</span>
            <SignOutButton />
          </div>

          <nav className={styles.nav}>
            {navigation.map((item) => (
              <Link key={item.href} href={item.href}>
                {item.label}
              </Link>
            ))}
          </nav>
        </header>

        <main className={styles.content}>{children}</main>
      </div>
    </div>
  );
}
