---
name: fix-bot
description: Triage a pasted Render log, stack trace, or "the bot did X but should do Y" report about main.py; find the root cause, fix it, verify offline, and ship. Use whenever the owner reports live bot misbehavior.
---

# Fix a live bot bug from the owner's report

The owner tests in production. His reports arrive as one of: a pasted Render log
line, a Python traceback, a screenshot-style description of the Telegram
conversation, or a voice transcript log line like
`Transcrição de voz | Chat: -5089425259 | Texto: Água de coco, R$ 10,00. Dinheiro.`

## Step 1 — Reconstruct the state before touching code

Answer these in writing before editing:

1. **Which entry point fired?** Text → `processar_gastos`; voice →
   `handle_voice`; button → `handle_expense_callbacks` (prefix `expense:`) or
   `handle_voice_callbacks` (prefix `voice:`).
2. **What was in `pending_expenses[chat_id]` at that moment?** Derive it from the
   report: a voice transcript tells you exactly which fields GPT pre-filled
   (e.g. "dinheiro" ⇒ `banco=EFECTIVO, forma=EFECTIVO`); the screen he saw tells
   you the `stage`.
3. **What did the bot do vs. what should it have done?**

If the report and the code disagree (the log shows a path that "can't happen"),
say so with the evidence — do not pick one story and build on it.

## Step 2 — Check the known failure classes first

| Symptom | Likely cause | Fix pattern |
|---|---|---|
| Bot asks for a field the user already gave (by voice or defaults) | A handler hardcodes the next step instead of resuming | Route through `continuar_apos_voz(chat_id, message_id)` — this exact bug shipped twice |
| "Informe a cotação" appears when it should auto-fetch | Rate API doesn't return PYG for that currency, or network failure swallowed | Check Render log for the `Cotação automática falhou` warning; `curl <api>/BRL` and inspect `rates.PYG` |
| `openai.PermissionDeniedError` / `model_not_found` | OpenAI project restricts models, or key created before model was allowed | Owner must allow `whisper-1` + `gpt-4o-mini` in project settings **and regenerate the key** |
| `openai` 429 `insufficient_quota` | No credits | Owner adds credits; nothing to fix in code |
| Whisper 400 on the audio | File not passed as tuple | Must be `("audio.ogg", file_content, "audio/ogg")`, never a bare BytesIO |
| Send/edit throws on special chars | `parse_mode="Markdown"` + user text containing `_` `*` `` ` `` | Strip/escape those chars in interpolated user content |
| Button tap does nothing, spinner forever | Handler path missing `bot.answer_callback_query` | Every branch answers, including error branches |
| Flow dies after "Escolha..." with no error | Tried `edit_message_text` on a USER message | `reply_to` first, then edit that reply's `message_id` |
| Bot silent for a user | `is_allowed` — chat not in `ALLOWED_CHAT_IDS` | Confirm the chat id with the owner; it's an env var on Render, not code |
| All state gone mid-flow | Render restarted/redeployed; `pending_expenses` is RAM | Not a bug; tell the owner to restart the entry |

## Step 3 — Fix at the cause

- Prefer deleting a wrong branch over adding a compensating one.
- If the fix is "advance the flow", it is `continuar_apos_voz` — never a copy of
  its logic.
- If the bug was invisible (an exception swallowed), add the `logger.warning` /
  `logger.exception` that would have shown it, in the same commit.
- New/changed user-facing strings: PT-BR, established emoji per field
  (see CLAUDE.md style section).

## Step 4 — Verify offline

```bash
python3 -m py_compile main.py && python3 .claude/skills/smoke-test/harness.py
```

Then **add a regression scenario** to the harness reproducing the report
(seed `pending_expenses` with the reconstructed state from Step 1, drive the
same input, assert the correct next screen). The fix is not done until the new
scenario passes and would have failed before the fix.

## Step 5 — Ship and hand back

- Commit on the designated `claude/...` branch: summary states the user-visible
  symptom, body states the root cause. Push with `git push -u origin <branch>`.
- PR only if he asked for one.
- Reply with: root cause in one sentence, what changed, and the exact live test
  script, e.g. *"After Render deploys, send a voice saying 'água de coco 10
  reais, dinheiro' — it should show the confirm screen directly, without asking
  for bank or cotação."* Never say it is deployed or verified live.
