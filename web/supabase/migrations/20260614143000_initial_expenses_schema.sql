create extension if not exists pgcrypto;

create type public.payment_method as enum (
  'cash',
  'debit_card',
  'credit_card',
  'bank_transfer',
  'qr',
  'other'
);

create type public.expense_source as enum (
  'manual',
  'telegram',
  'import'
);

create type public.sheet_sync_status as enum (
  'started',
  'succeeded',
  'failed'
);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create table public.categories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users (id) on delete cascade,
  name text not null,
  slug text not null check (slug = lower(slug)),
  is_active boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint categories_name_not_blank check (btrim(name) <> '')
);

comment on table public.categories is 'System and user-defined expense categories. Null user_id means a shared system category.';

create unique index categories_system_slug_idx
  on public.categories (slug)
  where user_id is null;

create unique index categories_user_slug_idx
  on public.categories (user_id, slug)
  where user_id is not null;

create index categories_user_id_idx on public.categories (user_id);

create table public.accounts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  name text not null,
  slug text not null check (slug = lower(slug)),
  is_active boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint accounts_name_not_blank check (btrim(name) <> '')
);

comment on table public.accounts is 'Bank, wallet, or financial-app source used to pay for an expense.';

create unique index accounts_user_slug_idx
  on public.accounts (user_id, slug);

create index accounts_user_id_idx on public.accounts (user_id);

create table public.expenses (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  description text not null,
  original_amount numeric(14, 2) not null check (original_amount > 0),
  currency text not null check (currency = upper(currency) and char_length(currency) = 3),
  exchange_rate numeric(14, 6) not null default 1 check (exchange_rate > 0),
  amount_pyg numeric(14, 2) not null check (amount_pyg >= 0),
  expense_date date not null,
  category_id uuid not null references public.categories (id) on delete restrict,
  account_id uuid not null references public.accounts (id) on delete restrict,
  payment_method public.payment_method not null,
  has_invoice boolean not null default false,
  source public.expense_source not null default 'manual',
  source_text text,
  source_payload jsonb,
  external_source_id text,
  notes text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint expenses_description_not_blank check (btrim(description) <> '')
);

comment on column public.expenses.currency is 'Normalized ISO-style currency code. Use PYG instead of legacy Gs.';

create index expenses_user_date_idx
  on public.expenses (user_id, expense_date desc);

create index expenses_user_created_at_idx
  on public.expenses (user_id, created_at desc);

create index expenses_category_id_idx on public.expenses (category_id);
create index expenses_account_id_idx on public.expenses (account_id);

create unique index expenses_external_source_idx
  on public.expenses (user_id, source, external_source_id)
  where external_source_id is not null;

create table public.telegram_connections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  telegram_user_id text,
  telegram_chat_id text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create unique index telegram_connections_chat_id_idx
  on public.telegram_connections (telegram_chat_id);

create index telegram_connections_user_id_idx
  on public.telegram_connections (user_id);

create table public.sheet_sync_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  status public.sheet_sync_status not null default 'started',
  started_at timestamptz not null default timezone('utc', now()),
  finished_at timestamptz,
  expenses_processed integer not null default 0 check (expenses_processed >= 0),
  last_synced_expense_updated_at timestamptz,
  error_message text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create index sheet_sync_runs_user_started_at_idx
  on public.sheet_sync_runs (user_id, started_at desc);

create or replace function public.validate_expense_relationships()
returns trigger
language plpgsql
as $$
declare
  account_owner uuid;
  category_owner uuid;
begin
  select user_id
    into account_owner
    from public.accounts
   where id = new.account_id;

  if account_owner is null then
    raise exception 'Account % does not exist.', new.account_id;
  end if;

  if account_owner <> new.user_id then
    raise exception 'Account % does not belong to user %.', new.account_id, new.user_id;
  end if;

  select user_id
    into category_owner
    from public.categories
   where id = new.category_id;

  if not found then
    raise exception 'Category % does not exist.', new.category_id;
  end if;

  if category_owner is not null and category_owner <> new.user_id then
    raise exception 'Category % does not belong to user %.', new.category_id, new.user_id;
  end if;

  return new;
end;
$$;

create trigger categories_set_updated_at
before update on public.categories
for each row
execute function public.set_updated_at();

create trigger accounts_set_updated_at
before update on public.accounts
for each row
execute function public.set_updated_at();

create trigger expenses_set_updated_at
before update on public.expenses
for each row
execute function public.set_updated_at();

create trigger telegram_connections_set_updated_at
before update on public.telegram_connections
for each row
execute function public.set_updated_at();

create trigger sheet_sync_runs_set_updated_at
before update on public.sheet_sync_runs
for each row
execute function public.set_updated_at();

create trigger expenses_validate_relationships
before insert or update of user_id, category_id, account_id
on public.expenses
for each row
execute function public.validate_expense_relationships();

alter table public.categories enable row level security;
alter table public.accounts enable row level security;
alter table public.expenses enable row level security;
alter table public.telegram_connections enable row level security;
alter table public.sheet_sync_runs enable row level security;

create policy "categories are visible to owners and everyone for system defaults"
  on public.categories
  for select
  to authenticated
  using (user_id is null or auth.uid() = user_id);

create policy "users can create their own categories"
  on public.categories
  for insert
  to authenticated
  with check (auth.uid() = user_id);

create policy "users can update their own categories"
  on public.categories
  for update
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "users can delete their own categories"
  on public.categories
  for delete
  to authenticated
  using (auth.uid() = user_id);

create policy "users can manage their own accounts"
  on public.accounts
  for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "users can manage their own expenses"
  on public.expenses
  for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "users can manage their own telegram connections"
  on public.telegram_connections
  for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "users can manage their own sheet sync runs"
  on public.sheet_sync_runs
  for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

insert into public.categories (name, slug)
values
  ('Uncategorized', 'uncategorized'),
  ('Mercado', 'mercado'),
  ('Alimentacao', 'alimentacao'),
  ('Casa', 'casa'),
  ('Transporte', 'transporte'),
  ('Saude', 'saude'),
  ('Atividade Fisica', 'atividade-fisica'),
  ('Beleza', 'beleza'),
  ('Mascota', 'mascota'),
  ('Assinaturas', 'assinaturas'),
  ('Educacao', 'educacao'),
  ('Tecnologia', 'tecnologia'),
  ('Lazer', 'lazer'),
  ('Roupas', 'roupas'),
  ('Presentes', 'presentes'),
  ('Doacoes', 'doacoes'),
  ('Investimentos', 'investimentos'),
  ('Taxas', 'taxas'),
  ('Impostos', 'impostos');
