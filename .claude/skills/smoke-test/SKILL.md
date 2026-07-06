---
name: smoke-test
description: Offline verification of main.py before pushing — stubs Telegram/Sheets/OpenAI and drives the real handlers through the expense flows. Use before committing ANY change to main.py, and extend it with a regression scenario when fixing a flow bug.
---

# Smoke-test the Telegram bot offline

This repo has no test suite and no staging: the owner merges, Render deploys, and
he finds bugs live on Telegram. This harness is the only pre-deploy verification.
It costs ~2 seconds and has already encoded every production regression to date.

## Run it

```bash
python3 -m py_compile main.py && python3 .claude/skills/smoke-test/harness.py
```

Pass criteria: exit code 0 and `All smoke-test scenarios passed.` If a scenario
fails, the harness prints the last 6 bot messages for that chat — read them; they
show exactly which screen the flow landed on.

## What the harness is

`harness.py` installs fake `telebot`, `flask`, `gspread`, `oauth2client`,
`openai`, and `dotenv` modules into `sys.modules`, then imports the **real**
`main.py` and calls its **real** handlers:

- `send_text(chat_id, "mercado 55000")` dispatches through the registered
  message handlers exactly as a Telegram text update would.
- `press(chat_id, "expense:banco:UENO")` dispatches a callback query, and
  **asserts that the handler called `answer_callback_query`** (a missed answer
  = infinite spinner on the phone).
- `main.planilha` is replaced with a fake sheet that records appended rows.
- `main.buscar_cotacao_guarani` is replaced with a deterministic rate (7300);
  scenarios can swap in a raising version to test the manual-rate fallback.
- Voice handlers can't be driven end-to-end offline (Whisper/GPT are external),
  so voice states are tested by seeding `main.pending_expenses[chat_id]` with the
  dict a voice message would have produced, then driving the rest of the flow.
  Keep doing it that way.

## Current scenarios (do not delete any)

1. Guided text flow end-to-end → exactly 10 columns in the right order
2. EFECTIVO bank skips the payment step and sets `forma = "EFECTIVO"`
3. Manual rate entry resumes at the first missing field (regression: voice said
   "dinheiro", bot must NOT ask for bank after the typed rate)
4. `continuar_apos_voz` auto-fetches the rate; falls back to manual prompt on API failure
5. `=SUM(...)` in a description arrives in the sheet prefixed with `'`
6. Forged callback values (`expense:banco:HACKED`) are rejected and not stored
7. Cancel clears pending state

## Rules for maintaining it

- **Fixed a flow bug?** Add a scenario that fails on the old code before you
  consider the fix done. Name it `(regression: <one-line description>)`.
- **Added a field/option/stage?** Extend scenario 1 (or add a sibling) so the
  10-column assertion and the happy path still describe reality. If the row
  gains a column, the assertion must change to 11 in the same commit — that
  forces you to remember the Apps Script indices (see CLAUDE.md).
- Use a **fresh chat_id per scenario** — `user_defaults` deliberately persists
  between expenses, and cross-contamination makes scenarios order-dependent.
- If `main.py` gains a new external dependency, stub it in the harness's fake
  module section, keeping import-time side effects harmless.
- Never make the harness import anything from the real `telebot`/`openai`
  packages — it must run in a bare container with only the stdlib.
