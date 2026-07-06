---
name: new-field
description: Recipe for extending the expense model — adding a bank/category/currency option, or adding a whole new field to the flow. Enumerates every touchpoint (stage machine, voice prompt, keyboards, save, sheet columns, Apps Script, web schema) so none is missed.
---

# Extend the expense model without breaking the pipeline

An expense field lives in up to NINE places. Missing one produces a bug that
only surfaces live. Pick the recipe that matches the request.

## Recipe A — New OPTION on an existing field (bank, category keyword, invoice label)

Cheap. Touchpoints:

1. The `*_OPTIONS` list in `main.py` (`BANK_OPTIONS`, etc.). The `VALID_*` sets
   derive automatically — don't edit them.
2. **The voice extraction prompt** in `extrair_gasto_do_texto`: banks are
   interpolated from `VALID_BANKS` automatically, but add a normalization rule
   if people say it differently than it's stored (e.g. `'"nu"/"nubank" → banco
   "NUBANK"'`). For a new category keyword, edit the `map` dict — keys are
   category names, values are UPPERCASE accent-free keywords (matching strips
   accents via `identificar_categoria`).
3. If the web app should recognize it too: `web/src/lib/telegram/categories.ts`
   keeps a **separate lowercase** keyword map — mirror the change there, and for
   a new category also check the seeded categories in
   `web/supabase/migrations/` (new categories need a migration or manual insert).

No stage-machine, sheet, or Apps Script changes. Verify with the smoke test.

## Recipe B — New CURRENCY

1. Add to `CURRENCY_OPTIONS` in `main.py`.
2. Add its spoken-form rule to the prompt in `extrair_gasto_do_texto`
   (`'"pesos"/"pesos argentinos" → moeda "ARS"'` style).
3. **Prove the rate API covers it before shipping:**
   ```bash
   curl -s https://api.exchangerate-api.com/v4/latest/XXX | head -c 300
   ```
   and confirm `rates.PYG` exists in the response. frankfurter.dev was adopted
   without this check and silently lacked PYG — that's why this line exists.
4. Web side stores ISO codes (`PYG` not `Gs`) — no change needed unless the code
   is nonstandard like `Gs`; nonstandard codes must be mapped in the webhook
   route (`web/src/app/api/telegram/webhook/route.ts` maps `GS → PYG` today).

## Recipe C — New FIELD on the expense (the expensive one)

Enumerate every touchpoint; do them in this order:

1. **Expense dict** — add the key (default `None`) in ALL creation sites:
   `iniciar_fluxo_interativo`, `handle_voice`, and any harness seeds. `None`
   means "not captured yet"; that convention drives the resume logic.
2. **Stage machine** — new `awaiting_<field>` stage + a `pedir_<field>(chat_id,
   message_id)` helper that edits the bot message with a keyboard built by
   `build_keyboard(NEW_OPTIONS, "expense:<field>")`.
3. **`continuar_apos_voz`** — insert the `elif expense.get("<field>") is None:`
   branch **in the flow order you want it asked**. This function is the single
   source of truth for "what's next"; if you find yourself writing next-step
   logic anywhere else, stop.
4. **Callback handler** — new `action[1] == "<field>"` branch in
   `handle_expense_callbacks`: validate against the `VALID_*` set, store, answer
   the callback, then advance by checking whether later fields are pre-filled
   (mirror how `forma` skips to the summary when `factura` is already set).
5. **Voice prompt** — add the field to `extrair_gasto_do_texto`'s JSON spec +
   normalization rules; then in `handle_voice`, read it, validate against the
   `VALID_*` set (null if invalid), and include it in both preview summaries.
6. **Summary + save** — `montar_resumo_gasto` line (pick an emoji, reuse the
   established set), and `salvar_gasto`: **append the new value at the END of
   `dados_linha`** — never insert mid-row. Strings go through
   `sanitizar_celula`. Also append in BOTH legacy branches of
   `processar_formato_legado` if the legacy format should carry it (usually it
   just gets a default).
7. **Sheet + Apps Script** — the sheet gains a column at the end (tell the owner
   to add a header). `google_script_telegram.gs` reads by index — if the report
   should use the new field, update the committed file AND remind the owner to
   paste it into the live Apps Script editor; the repo copy doesn't deploy.
8. **`user_defaults`** — decide whether the field should be remembered across
   expenses (banco/forma/factura are). If yes: read it in
   `iniciar_fluxo_interativo` and write it in `salvar_gasto`.
9. **Smoke test** — extend the harness: bump the column-count assertion,
   add the new step to scenario 1, and add a skip-when-prefilled scenario.
   Green harness = done.

Web/Supabase is a separate decision: the `expenses` table would need a
migration + `npm run types:local` regeneration. Ask the owner whether the web
schema should track the field now or wait — the two systems aren't wired yet.

## Before shipping (any recipe)

```bash
python3 -m py_compile main.py && python3 .claude/skills/smoke-test/harness.py
```

Commit message names the field/option and which recipe-level touchpoints were
hit. In the reply, give the owner one voice sentence and one text message to
test the new path live after Render deploys.
