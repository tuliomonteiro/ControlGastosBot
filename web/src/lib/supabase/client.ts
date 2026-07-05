import { createBrowserClient } from "@supabase/ssr";
import type { AppDatabase, AppSupabaseClient } from "@/lib/supabase/types";

export function createClient(): AppSupabaseClient {
  return createBrowserClient<AppDatabase>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
  );
}
