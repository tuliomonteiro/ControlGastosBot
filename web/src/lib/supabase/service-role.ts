import { createClient as createSupabaseClient } from "@supabase/supabase-js";
import type { AppDatabase, AppSupabaseClient } from "@/lib/supabase/types";

// Bypasses RLS. Only import this from server-only contexts (API routes) that
// perform their own authorization checks before touching the database —
// never from a Server Component, Server Action, or anything cookie/session based.
export function createServiceRoleClient(): AppSupabaseClient {
  return createSupabaseClient<AppDatabase>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    },
  );
}
