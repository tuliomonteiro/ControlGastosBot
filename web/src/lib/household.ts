// The app is single-tenant in data terms: every row in Supabase belongs to one
// fixed owner (the same auth.users UUID the bot writes to via SUPABASE_USER_ID),
// regardless of which allow-listed identity is currently logged in. Multiple
// people can authenticate (see household_members + the RLS policies in
// 20260917190000_household_sharing.sql), but they all read and write the same
// household's data rather than each getting their own empty tenant.
export function getHouseholdUserId(): string {
  const id = process.env.SUPABASE_USER_ID;

  if (!id) {
    throw new Error(
      "SUPABASE_USER_ID is not configured. Set it to the household owner's auth.users UUID.",
    );
  }

  return id;
}
