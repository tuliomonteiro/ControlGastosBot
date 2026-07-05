import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

function getAllowedEmails() {
  return (process.env.ALLOWED_EMAILS ?? "")
    .split(",")
    .map((value) => value.trim().toLowerCase())
    .filter(Boolean);
}

function getAllowedDomain() {
  return process.env.ALLOWED_GOOGLE_WORKSPACE_DOMAIN?.trim().toLowerCase();
}

export function isEmailAllowed(email?: string | null) {
  if (!email) {
    return false;
  }

  const normalizedEmail = email.toLowerCase();
  const allowedEmails = getAllowedEmails();
  const allowedDomain = getAllowedDomain();

  if (allowedEmails.includes(normalizedEmail)) {
    return true;
  }

  if (!allowedDomain) {
    return false;
  }

  return normalizedEmail.endsWith(`@${allowedDomain}`);
}

export function buildLoginUrl(nextPath?: string, error?: string) {
  const searchParams = new URLSearchParams();

  if (nextPath) {
    searchParams.set("next", nextPath);
  }

  if (error) {
    searchParams.set("error", error);
  }

  const queryString = searchParams.toString();
  return queryString ? `/login?${queryString}` : "/login";
}

export async function getCurrentUser() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return user;
}

export async function requireAllowedUser(nextPath: string) {
  const user = await getCurrentUser();

  if (!user) {
    redirect(buildLoginUrl(nextPath));
  }

  if (!isEmailAllowed(user.email)) {
    redirect(buildLoginUrl(undefined, "unauthorized"));
  }

  return user;
}
