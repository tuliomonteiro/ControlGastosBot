import { redirect } from "next/navigation";
import { GoogleSignInButton } from "@/components/auth/google-sign-in-button";
import { getCurrentUser, isEmailAllowed } from "@/lib/auth";
import styles from "./login.module.css";

const errorMessages: Record<string, string> = {
  missing_code: "Google returned without an authorization code. Try signing in again.",
  oauth_exchange_failed: "The Google login could not be completed. Re-run the flow.",
  unauthorized: "This account is not allowed to access ControlGastos Web.",
};

type LoginPageProps = {
  searchParams: Promise<{
    error?: string;
    next?: string;
  }>;
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const [{ error, next }, user] = await Promise.all([searchParams, getCurrentUser()]);

  if (user?.email && isEmailAllowed(user.email)) {
    redirect(next && next.startsWith("/") ? next : "/dashboard");
  }

  const errorMessage = error ? errorMessages[error] : null;

  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <p className={styles.eyebrow}>ControlGastos Web</p>
        <h1>Single-user access through Google.</h1>
        <p>
          Sign in with the Google account you will allowlist in Supabase. The app
          will reject any other account even if OAuth succeeds.
        </p>

        {errorMessage ? <div className={styles.error}>{errorMessage}</div> : null}

        <div className={styles.actions}>
          <GoogleSignInButton next={next} />
        </div>
      </section>
    </main>
  );
}
