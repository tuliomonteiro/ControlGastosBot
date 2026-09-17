import { NextResponse } from "next/server";
import { buildLoginUrl, isEmailAllowed } from "@/lib/auth";
import { createClient } from "@/lib/supabase/server";

function normalizeNext(value: string | null) {
  if (!value || !value.startsWith("/")) {
    return "/dashboard";
  }

  return value;
}

export async function GET(request: Request) {
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get("code");
  const next = normalizeNext(requestUrl.searchParams.get("next"));
  const supabase = await createClient();

  // Render (and most reverse-proxied hosts) terminate TLS at the edge and
  // forward to the container over an internal address, so requestUrl.origin
  // can reflect that internal host:port instead of the public domain.
  // NEXT_PUBLIC_SITE_URL is the source of truth here, same as the sign-in
  // button already does for the outbound redirectTo.
  const origin = process.env.NEXT_PUBLIC_SITE_URL || requestUrl.origin;

  if (!code) {
    return NextResponse.redirect(new URL(buildLoginUrl(next, "missing_code"), origin));
  }

  const { error } = await supabase.auth.exchangeCodeForSession(code);

  if (error) {
    return NextResponse.redirect(
      new URL(buildLoginUrl(next, "oauth_exchange_failed"), origin),
    );
  }

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user?.email || !isEmailAllowed(user.email)) {
    await supabase.auth.signOut();
    return NextResponse.redirect(
      new URL(buildLoginUrl(undefined, "unauthorized"), origin),
    );
  }

  return NextResponse.redirect(new URL(next, origin));
}
