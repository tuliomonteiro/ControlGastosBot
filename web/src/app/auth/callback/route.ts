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

  if (!code) {
    return NextResponse.redirect(new URL(buildLoginUrl(next, "missing_code"), requestUrl.origin));
  }

  const { error } = await supabase.auth.exchangeCodeForSession(code);

  if (error) {
    return NextResponse.redirect(
      new URL(buildLoginUrl(next, "oauth_exchange_failed"), requestUrl.origin),
    );
  }

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user?.email || !isEmailAllowed(user.email)) {
    await supabase.auth.signOut();
    return NextResponse.redirect(
      new URL(buildLoginUrl(undefined, "unauthorized"), requestUrl.origin),
    );
  }

  return NextResponse.redirect(new URL(next, requestUrl.origin));
}
