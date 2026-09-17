-- Lets a second Supabase Auth identity (e.g. a spouse) read and write the same
-- household's data. The app remains single-tenant in data terms (everything is
-- still owned by one fixed user_id, matching main.py's SUPABASE_USER_ID) but
-- multi-user in auth terms: any authenticated identity listed in
-- household_members may act on that owner's rows.

create table public.household_members (
  user_id uuid primary key references auth.users (id) on delete cascade,
  created_at timestamptz not null default timezone('utc', now())
);

comment on table public.household_members is
  'Auth identities allowed to read/write the household owner''s data. Membership is managed by service-role SQL only, never through the app.';

alter table public.household_members enable row level security;

create policy "members can see who else is in the household"
  on public.household_members
  for select
  to authenticated
  using ((select auth.uid()) in (select hm.user_id from public.household_members hm));

-- Seed the existing owner so the household is never empty.
insert into public.household_members (user_id)
values ('d1163cb4-8535-4c5a-bc2a-46af84f1a5ad')
on conflict do nothing;

create or replace function public.is_household_member()
returns boolean
language sql
stable
security invoker
set search_path = ''
as $$
  select exists (
    select 1 from public.household_members where user_id = (select auth.uid())
  );
$$;

comment on function public.is_household_member() is
  'True when the current auth user is allowed to act on the household''s data.';

-- Hardening for two pre-existing functions the security advisor flagged with a
-- mutable search_path (unrelated to sharing, fixed while touching this file).
alter function public.set_updated_at() set search_path = '';
alter function public.validate_expense_relationships() set search_path = '';

-- accounts: single ALL policy today, replace outright.
drop policy "users can manage their own accounts" on public.accounts;

create policy "household members can manage the household's accounts"
  on public.accounts
  for all
  to authenticated
  using (public.is_household_member() and user_id = 'd1163cb4-8535-4c5a-bc2a-46af84f1a5ad'::uuid)
  with check (public.is_household_member() and user_id = 'd1163cb4-8535-4c5a-bc2a-46af84f1a5ad'::uuid);

-- expenses: single ALL policy today, replace outright.
drop policy "users can manage their own expenses" on public.expenses;

create policy "household members can manage the household's expenses"
  on public.expenses
  for all
  to authenticated
  using (public.is_household_member() and user_id = 'd1163cb4-8535-4c5a-bc2a-46af84f1a5ad'::uuid)
  with check (public.is_household_member() and user_id = 'd1163cb4-8535-4c5a-bc2a-46af84f1a5ad'::uuid);

-- telegram_connections: single ALL policy today, replace outright.
drop policy "users can manage their own telegram connections" on public.telegram_connections;

create policy "household members can manage the household's telegram connections"
  on public.telegram_connections
  for all
  to authenticated
  using (public.is_household_member() and user_id = 'd1163cb4-8535-4c5a-bc2a-46af84f1a5ad'::uuid)
  with check (public.is_household_member() and user_id = 'd1163cb4-8535-4c5a-bc2a-46af84f1a5ad'::uuid);

-- sheet_sync_runs: single ALL policy today, replace outright.
drop policy "users can manage their own sheet sync runs" on public.sheet_sync_runs;

create policy "household members can manage the household's sheet sync runs"
  on public.sheet_sync_runs
  for all
  to authenticated
  using (public.is_household_member() and user_id = 'd1163cb4-8535-4c5a-bc2a-46af84f1a5ad'::uuid)
  with check (public.is_household_member() and user_id = 'd1163cb4-8535-4c5a-bc2a-46af84f1a5ad'::uuid);

-- categories: four separate policies today (system categories have a null
-- user_id and stay visible to everyone regardless of household membership).
drop policy "categories are visible to owners and everyone for system defaul" on public.categories;
drop policy "users can create their own categories" on public.categories;
drop policy "users can update their own categories" on public.categories;
drop policy "users can delete their own categories" on public.categories;

create policy "categories are visible to household members and everyone for system defaults"
  on public.categories
  for select
  to authenticated
  using (user_id is null or (public.is_household_member() and user_id = 'd1163cb4-8535-4c5a-bc2a-46af84f1a5ad'::uuid));

create policy "household members can create household categories"
  on public.categories
  for insert
  to authenticated
  with check (public.is_household_member() and user_id = 'd1163cb4-8535-4c5a-bc2a-46af84f1a5ad'::uuid);

create policy "household members can update household categories"
  on public.categories
  for update
  to authenticated
  using (public.is_household_member() and user_id = 'd1163cb4-8535-4c5a-bc2a-46af84f1a5ad'::uuid)
  with check (public.is_household_member() and user_id = 'd1163cb4-8535-4c5a-bc2a-46af84f1a5ad'::uuid);

create policy "household members can delete household categories"
  on public.categories
  for delete
  to authenticated
  using (public.is_household_member() and user_id = 'd1163cb4-8535-4c5a-bc2a-46af84f1a5ad'::uuid);
