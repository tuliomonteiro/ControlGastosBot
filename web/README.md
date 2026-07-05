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
# service-role key, server-only, bypasses RLS — used by the Telegram webhook
SUPABASE_SERVICE_ROLE_KEY=
# shared secret set on the bot's setWebhook call; rejects unauthenticated webhook calls
TELEGRAM_WEBHOOK_SECRET=
```

Use `ALLOWED_EMAILS` for the strictest single-user setup. Only use `ALLOWED_GOOGLE_WORKSPACE_DOMAIN` if you want any user from that workspace domain to be able to sign in.

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
