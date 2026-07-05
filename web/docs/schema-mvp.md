# MVP Schema Notes

This project's first database schema targets a single authenticated user while
keeping the path open for future multi-user expansion.

## Decisions Locked

- `expenses` only, no income or transfers yet
- `accounts` mean bank / wallet / financial app used for payment
- `categories` can be bot-suggested but remain editable later
- `has_invoice` is a boolean only
- edits overwrite rows in place; no audit trail in MVP

## Modeling Choices

- `categories` support both system defaults and user-defined values
  - system categories have `user_id = null`
  - custom categories have `user_id = auth.users.id`
- `accounts` are user-owned
- `expenses` are user-owned
- `payment_method` is a database enum on the expense row
- `currency` is normalized to ISO-style codes such as `PYG`, `USD`, `BRL`
  - legacy bot values like `Gs` should be mapped to `PYG`
- Telegram ingestion metadata is preserved with:
  - `source`
  - `source_text`
  - `source_payload`
  - `external_source_id`

## Migration Layout

- [20260614143000_initial_expenses_schema.sql](/Users/tuliomonteirodasilva/projects/controlgastos-web/supabase/migrations/20260614143000_initial_expenses_schema.sql)

## Seeded Defaults

The initial migration seeds shared system categories based on the current bot's
category map. Accounts are not seeded because they are user-specific.
