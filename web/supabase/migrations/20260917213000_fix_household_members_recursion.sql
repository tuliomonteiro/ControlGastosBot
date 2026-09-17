-- The household_members SELECT policy queried household_members itself, and
-- is_household_member() (SECURITY INVOKER) re-triggered that same policy on its
-- own internal lookup -> infinite recursion (Postgres error 42P17), breaking
-- every page that touches any household-scoped table.
--
-- Fix: make is_household_member() SECURITY DEFINER so its internal read of
-- household_members bypasses RLS instead of re-entering it. Safe to do here
-- because the function takes no caller-supplied identifiers - it only ever
-- checks (select auth.uid()), so it can only ever answer "is the CALLING user
-- a member", never leak another user's membership.
create or replace function public.is_household_member()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.household_members where user_id = (select auth.uid())
  );
$$;

-- Route the table's own SELECT policy through the same (now recursion-safe)
-- function instead of querying itself directly.
drop policy "members can see who else is in the household" on public.household_members;

create policy "members can see who else is in the household"
  on public.household_members
  for select
  to authenticated
  using (public.is_household_member());
