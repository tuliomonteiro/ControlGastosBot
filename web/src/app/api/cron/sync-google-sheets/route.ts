import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    ok: true,
    message: "Daily Google Sheets sync placeholder",
    syncedAt: new Date().toISOString(),
  });
}
