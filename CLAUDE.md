# CLAUDE.md — Operating Manual

Personal expense tracker. One owner (Tulio), Brazilian living in Paraguay: UX is
Brazilian Portuguese, money is Paraguayan guaraní (Gs/PYG), some Spanish terms
("factura", "efectivo") are intentional. Do not "correct" the language mix.

## The two systems (and the one that actually runs)

1. **`main.py`** — Python Telegram bot. Flask webhook on Render, auto-deploys from
   `main`. Writes expenses directly to a Google Sheet via `gspread` + a service
   account `credentials.json` (never in git). **This is production.**
2. **`web/`** — Next.js 16 + React 19 + Supabase app. Migration target, partially
   built. The `/api/telegram/webhook` route exists but the Python bot does NOT call
   it yet. The Sheets-sync cron is a placeholder. **Not wired to production.**
3. **`google_script_telegram.gs`** — Apps Script pasted into the spreadsheet (not
   deployed from this repo). Sends weekly/monthly Telegram reports by reading sheet
   columns **by numeric index**. The committed copy is reference only; the live copy
   lives in Google. Keep them in sync when you change it.

A change to one system rarely requires touching the others — but see the
column-order rule below for the one coupling that bites.

## How the owner works (match this loop)

- Every change: develop on the designated `claude/...` branch → commit → push →
  PR only when explicitly asked ("create a PR"). Never push to `main`.
- There is **no test suite and no staging**. The owner merges, Render deploys, and
  he tests live by talking to the bot on Telegram. When it breaks he pastes the
  Render log or the bot's error message back into chat. Therefore:
  - Error messages must surface the real exception (`type(e).__name__: e`), and
    failures must `logger.exception(...)` / `logger.warning(...)` — a silent
    `except: pass` costs a full deploy-test-report cycle to diagnose.
  - Before pushing, run the offline smoke test (see `/smoke-test` skill). It is the
    only pre-deploy verification that exists.
- After shipping, tell him exactly what to test ("send a voice saying X, expect Y")
  and say "after Render deploys" — never claim it is live or verified.
- Commits: short imperative summary, body explains the why. Prefixes like `fix:` /
  `feat:` / `security:` are used but not enforced.

## Bot conventions (`main.py`)

**Data model.** One in-memory dict per chat in `pending_expenses[chat_id]` with keys
`desc, valor, fecha, moeda, cotizacao, valor_final, cat, banco, forma, factura,
stage`. `None` means "not captured yet". `user_defaults[chat_id]` remembers last
banco/forma and exchange rates for pre-filling new expenses; `factura` is stored
there too (for the sheet-row history) but deliberately NOT read back to pre-fill —
it varies per purchase, so the guided flow always asks it fresh. **All of this is
RAM — every Render deploy or restart wipes it.** Never build a feature that
assumes state survives a restart.

**Stage machine.** `stage` values: `awaiting_currency`, `awaiting_exchange_rate`,
`awaiting_bank`, `awaiting_payment`, `awaiting_invoice`, `awaiting_confirmation`,
`voice_preview`, `voice_full_preview`. Text input is only interpreted as flow input
when a pending expense's stage expects it (today: `awaiting_exchange_rate`).

**The resume rule (most important rule in this file).** Fields can be pre-filled
from voice, from `user_defaults`, or from earlier steps. Any code that advances the
flow must call **`continuar_apos_voz(chat_id, message_id)`** — which fetches the
rate if missing, then asks only for the first `None` field — instead of hardcoding
"next show bank". Two real production bugs came from violating this.

**Special value: EFECTIVO.** Cash. When `banco == "EFECTIVO"`, set
`forma = "EFECTIVO"` in the same breath and skip the payment-method step. Both the
callback handler and the voice extractor already do this; new paths must too.

**Guards on every entry point** (message handler, callback handler, new route):
- `is_allowed(chat_id)` first line; return silently if not allowed.
- Callback payloads validated against `VALID_BANKS` / `VALID_PAYMENTS` /
  `VALID_INVOICES` / `VALID_CURRENCIES` before use — callback data is attacker
  input, Telegram clients can send anything.
- Every callback handler path ends with `bot.answer_callback_query(call.id, ...)`,
  otherwise the user's Telegram shows an infinite spinner.
- Every string written to the sheet goes through `sanitizar_celula()` (formula
  injection guard).

**Sheet row format — append-only contract.** `salvar_gasto` writes exactly:
`[desc, valor, moeda, cotizacao, valor_final_formatted, fecha, cat, banco, forma,
factura]` (indices 0–9). The Apps Script reads `linha[4]` (valor final), `linha[5]`
(fecha), `linha[6]` (categoria), `linha[9]` (factura) **by index**, and existing
sheet rows since 2024 use this order. Never reorder or insert columns — new columns
go at the END, and the Apps Script must be updated in the same PR.

**Money & dates.**
- `valor_final` is written as a pt-BR formatted STRING (`1.234.567` via
  `formatar_guaranis`); `valor` is a raw number; `cotizacao` is an `int`.
- Currency code is `"Gs"` in the bot and the sheet. The web app uses `"PYG"`.
  Map at the boundary; never rename either side.
- Dates are `DD/MM/YYYY` strings. `datetime.now()` is server time (Render = UTC),
  so late-evening Paraguay expenses can get tomorrow's date. Known quirk — flag it
  if relevant, don't silently "fix" it.
- User-typed amounts go through `parse_valor_brlike` (handles `155k`, `30 mil`,
  `33,50`). Reuse it; don't write a new parser.

**Voice pipeline.** OGG bytes → Whisper (`model="whisper-1"`, `language="pt"`,
file as the tuple `("audio.ogg", content, "audio/ogg")` — a bare BytesIO fails) →
GPT (`gpt-4o-mini`, `response_format={"type": "json_object"}`, `temperature=0`)
extracting all fields. Every extracted field is validated against the `VALID_*`
sets and nulled if invalid — the model's output is untrusted. If you add a field or
option, update the extraction prompt in `extrair_gasto_do_texto` in the same
change, including its normalization rules ("dinheiro" → EFECTIVO etc.).

**Exchange rates.** `buscar_cotacao_guarani` hits
`api.exchangerate-api.com/v4/latest/{CUR}` and multiplies by
`EXCHANGE_RATE_SPREAD` (default 1.01, the card spread — intentional, keep it).
History lesson: frankfurter.dev was used first and silently lacked PYG. **Before
pointing at any rate API, curl it and confirm PYG is in the response.**

**Telegram API facts** the code relies on:
- `bot.edit_message_text` only works on messages the BOT sent. To continue a flow
  after a user text message, `bot.reply_to(...)` first, then pass that reply's
  `message_id` to `continuar_apos_voz` / `pedir_*`.
- Messages use `parse_mode="Markdown"`. Interpolating user content containing `_`,
  `*`, `` ` `` can make the send throw. Keep interpolated user text short
  (descriptions are uppercased words, usually safe); if sending raw transcripts,
  consider stripping those chars.

**Style.** All user-visible strings are PT-BR with an emoji prefix per line
(📝 desc, 🏷️ cat, 💵 valor, 📅 data, 🏦 banco, 💳 forma, 🧾 factura, 📈 cotação —
reuse these, don't invent new ones). Code identifiers are Portuguese
(`salvar_gasto`, `pedir_banco`) — follow that. The global `map` (category keyword
dict) shadows the builtin; it's everywhere, leave the name alone.

## Web conventions (`web/`)

- Server components + server actions; no client-side data fetching, no UI library.
- Every protected page and every server action starts with
  `await requireAllowedUser(path)`. No exceptions.
- Supabase clients: `lib/supabase/server.ts` (anon, RLS-bound) for user-facing
  code; `lib/supabase/service-role.ts` (bypasses RLS) ONLY inside
  `/api/telegram/webhook`. Never leak the service-role client elsewhere.
- All DB access lives in `lib/data/expenses.ts` — pages and actions call those
  functions, never inline `.from(...)` queries in components.
- Mutating server actions call `revalidatePath` for every affected route.
- Schema changes = new file via `npm run migration:new`, then regenerate
  `src/lib/database.types.ts` with `npm run types:local` / `types:remote`.
  **`database.types.ts` is generated — never hand-edit it.**
- `proxy.ts` is Next 16's middleware (renamed from `middleware.ts`) — don't
  "helpfully" rename it back.

## Named mistakes a model will make here, and the rule that prevents each

| # | Mistake | Rule |
|---|---------|------|
| 1 | Hardcoding the next flow step ("now show bank") after handling one field | Always advance via `continuar_apos_voz`. Happened twice in production. |
| 2 | Reordering / inserting sheet columns | New columns append at the end; update Apps Script indices in the same PR. |
| 3 | Writing to the sheet without `sanitizar_celula` on strings | Every string cell goes through it. |
| 4 | New handler without `is_allowed` / callback without validation / missing `answer_callback_query` | Apply the "guards on every entry point" checklist verbatim. |
| 5 | Renaming `Gs` → `PYG` (or vice versa) for "consistency" | They are different systems' codes. Map at the boundary only. |
| 6 | `except: pass` or generic error text | Log with `logger.exception`/`warning`; user-facing errors include `type(e).__name__`. |
| 7 | Feature that stores state across restarts in `pending_expenses`/`user_defaults` | RAM only. If durable state is needed, say so and propose Supabase — don't fake it. |
| 8 | Editing `web/src/lib/database.types.ts` by hand | Generated file; change the migration and regenerate. |
| 9 | `edit_message_text` on a user's message | Only bot messages are editable; `reply_to` then edit that. |
| 10 | English strings in bot replies | PT-BR with the established emoji per field. |
| 11 | Assuming a rate API supports PYG | curl the endpoint and check `rates.PYG` exists before adopting it. |
| 12 | Claiming "tests pass" or "deployed and working" | There are no tests; deploys happen on merge. Say what was verified (compile + smoke test) and what the owner should test live. |
| 13 | New import without updating `requirements.txt` | Unpinned name in `requirements.txt` in the same commit. |
| 14 | Adding a field without touching the voice prompt | Field changes touch `extrair_gasto_do_texto` too — see `/new-field` skill. |

## Quality bar per deliverable (checkable)

**Any `main.py` change:**
- [ ] `python3 -m py_compile main.py` passes
- [ ] `/smoke-test` harness passes (or you state exactly why a scenario is N/A)
- [ ] New/changed handlers satisfy all four entry-point guards
- [ ] Flow advancement goes through `continuar_apos_voz`
- [ ] New env vars: read via `os.getenv` with a default, documented in README's env section
- [ ] No secrets, no `credentials.json`, no `.env` content in the diff

**Any `web/` change:**
- [ ] `npm run lint` and `npx tsc --noEmit` pass (run in `web/`)
- [ ] Protected surface calls `requireAllowedUser`; mutations `revalidatePath`
- [ ] Schema change ⇒ migration file + regenerated types, both in the diff

**Any PR:**
- [ ] On the designated `claude/...` branch, pushed with `git push -u origin <branch>`
- [ ] Body describes the user-visible behavior change and what to test after deploy
- [ ] Created only when explicitly requested

**Any bug fix from a pasted log:**
- [ ] Root cause stated (which line, which state) before the edit — not pattern-matched
- [ ] The fix is at the cause, not a symptom patch; if the log contradicts the report, say so

## When uncertain — exact escalation rules

**Proceed without asking** (reversible, inside the request's scope): bug fixes in
flow logic, adding logging, refactors preserving behavior, copy tweaks in PT-BR,
adding an option to an existing list (bank, category keyword).

**Ask first, always:**
- Anything that changes the sheet's column layout or rewrites existing rows
- Deleting/renaming env vars, or changing what an existing env var means
- Switching a paid/external provider (OpenAI models, rate API) beyond what was asked
- Anything touching auth: `ALLOWED_CHAT_IDS`, `ALLOWED_EMAILS`, webhook secrets
- Wiring the bot to the web app's webhook (architecture decision he's staging deliberately)
- Any destructive git operation

**When a live report and the code disagree** (e.g., the log shows a path that
"can't happen"): report the discrepancy with the evidence instead of picking one
story and building on it.

**When a question is really a question** (he's thinking out loud, asking "what do
you think", "how does X work"): answer it. Don't start editing until he says do it.
