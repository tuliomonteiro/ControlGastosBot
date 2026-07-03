import { NextRequest, NextResponse } from "next/server";
import { COOKIE_NAME, computeToken } from "@/lib/auth";

export async function proxy(request: NextRequest) {
  const secret = process.env.SESSION_SECRET;

  // If SESSION_SECRET isn't set, skip auth (useful during initial local dev)
  if (!secret) return NextResponse.next();

  const token = request.cookies.get(COOKIE_NAME)?.value;
  const expected = await computeToken(secret);

  if (token !== expected) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("from", request.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  // Protect all routes except login, auth API, and Next.js internals
  matcher: ["/((?!login|api/auth|_next/static|_next/image|favicon.ico).*)"],
};
