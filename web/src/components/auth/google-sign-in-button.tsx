"use client";

import { createClient } from "@/lib/supabase/client";

type GoogleSignInButtonProps = {
  next?: string;
};

export function GoogleSignInButton({ next = "/dashboard" }: GoogleSignInButtonProps) {
  const handleClick = async () => {
    const supabase = createClient();
    const origin = process.env.NEXT_PUBLIC_SITE_URL || window.location.origin;
    const redirectTo = new URL("/auth/callback", origin);

    if (next.startsWith("/")) {
      redirectTo.searchParams.set("next", next);
    }

    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: redirectTo.toString(),
      },
    });
  };

  return (
    <button type="button" onClick={handleClick}>
      Continue With Google
    </button>
  );
}
