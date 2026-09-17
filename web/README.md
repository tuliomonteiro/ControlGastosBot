## ControlGastos Web

Next.js app for the ControlGastos migration target:
- Google login through Supabase Auth
- protected dashboard, expenses, and integrations routes
- Telegram webhook and daily Sheets sync placeholders

## Environment

Copy `.env.example` to `.env.local` and fill in:

```bash
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=
NEXT_PUBLIC_SITE_URL=http://localhost:3000
ALLOWED_EMAILS=you@yourdomain.com
# optional alternative to a specific email
ALLOWED_GOOGLE_WORKSPACE_DOMAIN=
# the auth.users UUID that owns all household data (same value as the bot's
# SUPABASE_USER_ID) — see "Sharing with another person" below
SUPABASE_USER_ID=
# service-role key, server-only, bypasses RLS — used by the Telegram webhook
SUPABASE_SERVICE_ROLE_KEY=
# shared secret set on the bot's setWebhook call; rejects unauthenticated webhook calls
TELEGRAM_WEBHOOK_SECRET=
```

Use `ALLOWED_EMAILS` for the strictest single-user setup. Only use `ALLOWED_GOOGLE_WORKSPACE_DOMAIN` if you want any user from that workspace domain to be able to sign in.

## Sharing with another person

The app is single-tenant in data terms — every row belongs to one fixed
`user_id` (`SUPABASE_USER_ID`) — but multiple Supabase Auth identities can be
authorized to read/write that same data. This is different from giving someone
their own account: they see and edit the exact same household ledger, not a
separate empty one.

To add someone:

1. Add their email to `ALLOWED_EMAILS` (comma-separated) so they can log in at all.
2. Have them sign in once through `/login`. This creates their `auth.users` row
   but grants no data access yet — until step 3, they'll see an empty dashboard.
3. Look up their new UUID (Supabase dashboard → Authentication → Users) and add
   it to `household_members`:
   ```sql
   insert into public.household_members (user_id) values ('their-uuid-here');
   ```
   This must be run as service-role SQL (the Supabase SQL Editor, or the
   Supabase MCP tools) — the table has no insert policy for the `authenticated`
   role, so it can't be self-managed through the app.

See `supabase/migrations/20260917190000_household_sharing.sql` for the RLS
policies that make this work: every policy checks `is_household_member()` in
addition to the row's fixed owner `user_id`, so membership is enforced at the
database level, not just in application code.

## Local development

```bash
npm run dev
```

## Supabase CLI Workflow

The Supabase CLI is installed as a local dev dependency.

Common commands:

```bash
npm run supabase:start
npm run supabase:stop
npm run supabase:status
npm run db:reset
npm run db:push
npm run db:lint
npm run types:local
npm run types:remote
```

### First-time remote setup

```bash
npm run supabase:login
npm run supabase:link -- --project-ref ghckqkkfpyzvcehmdtsq
npm run db:push
npm run types:remote
```

The link step will ask for your remote database password.

### Local database workflow

Requires Docker-compatible tooling:

```bash
npm run supabase:start
npm run db:reset
npm run types:local
```

The local stack uses the auth redirect URLs defined in `supabase/config.toml`.

## Auth flow

- `/login` starts Google OAuth with Supabase
- `/auth/callback` exchanges the code for a session
- protected routes are guarded server-side
- unauthorized emails are rejected even if Google auth succeeds

## Telegram webhook

`/api/telegram/webhook` writes expenses on behalf of a user resolved from the
`telegram_connections` table. Because Telegram calls it without a Supabase
session, it authenticates via a shared secret (`TELEGRAM_WEBHOOK_SECRET`,
checked against the `X-Telegram-Bot-Api-Secret-Token` header — set the same
value as the `secret_token` param when calling Telegram's `setWebhook`) and
uses a service-role client (`SUPABASE_SERVICE_ROLE_KEY`) to bypass RLS instead
of relying on a user session that doesn't exist for webhook calls.

## Routes

- `/`
- `/login`
- `/dashboard`
- `/expenses`
- `/settings/integrations`
- `/api/telegram/webhook`
- `/api/cron/sync-google-sheets`
