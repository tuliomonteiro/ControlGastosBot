-- Security advisor flagged is_household_member() (now SECURITY DEFINER, see
-- 20260917213000) as callable by anon and authenticated via
-- /rest/v1/rpc/is_household_member. This project grants EXECUTE on new
-- public-schema functions to anon/authenticated/service_role directly (not
-- just via PUBLIC), so both the PUBLIC grant and the anon-specific one need
-- revoking - confirmed via has_function_privilege() that revoking from PUBLIC
-- alone left anon still able to execute.
--
-- authenticated must keep EXECUTE: every RLS policy that calls this function
-- runs under that role, and revoking it would break policy evaluation, not
-- just direct RPC calls. anon has no legitimate use for it, and the function
-- takes no caller-supplied identifiers - it only ever answers "is the CALLING
-- user a member" - so a direct anon RPC call would just have returned false,
-- never leaked another user's membership. Revoking anyway to close the
-- unnecessary public surface the advisor flagged.
revoke execute on function public.is_household_member() from public;
revoke execute on function public.is_household_member() from anon;
grant execute on function public.is_household_member() to authenticated;
