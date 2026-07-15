#!/usr/bin/env python3
"""Offline smoke test for main.py — no network, no Telegram, no Google, no OpenAI.

Stubs every external dependency, imports main.py, and drives the real handlers
through the expense flows. Run from the repo root:

    python3 .claude/skills/smoke-test/harness.py

Exit code 0 = all scenarios passed. Any assertion failure prints the scenario
name and the bot's message log for that chat.
"""
import os
import sys
import types as pytypes
from types import SimpleNamespace

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, REPO_ROOT)
os.chdir(REPO_ROOT)

# Deterministic environment: no allowlist (everyone allowed), no OpenAI client.
for var in ("ALLOWED_CHAT_IDS", "OPENAI_API_KEY", "TELEGRAM_TOKEN", "WEBHOOK_SECRET"):
    os.environ.pop(var, None)


# --- Fake telebot -----------------------------------------------------------
class FakeKeyboard:
    def __init__(self, row_width=2):
        self.buttons = []

    def add(self, *btns):
        self.buttons.extend(btns)

    @property
    def callback_datas(self):
        return [b.callback_data for b in self.buttons]


class FakeButton:
    def __init__(self, text, callback_data=None, **kw):
        self.text = text
        self.callback_data = callback_data


class FakeBot:
    def __init__(self, token=None, *a, **k):
        self.outbox = []  # dicts: kind, chat_id, text, markup, message_id
        self._mid = 1000
        self.message_handlers = []
        self.callback_handlers = []

    def message_handler(self, **filters):
        def deco(fn):
            self.message_handlers.append((filters, fn))
            return fn
        return deco

    def callback_query_handler(self, func=None, **k):
        def deco(fn):
            self.callback_handlers.append((func, fn))
            return fn
        return deco

    def _record(self, kind, chat_id, text, markup=None, message_id=None):
        self._mid += 1
        entry = dict(kind=kind, chat_id=chat_id, text=text, markup=markup,
                     message_id=message_id or self._mid)
        self.outbox.append(entry)
        return SimpleNamespace(message_id=entry["message_id"],
                               chat=SimpleNamespace(id=chat_id))

    def reply_to(self, message, text, **kw):
        return self._record("reply", message.chat.id, text, kw.get("reply_markup"))

    def send_message(self, chat_id, text, **kw):
        return self._record("send", chat_id, text, kw.get("reply_markup"))

    def edit_message_text(self, text, chat_id=None, message_id=None, **kw):
        return self._record("edit", chat_id, text, kw.get("reply_markup"), message_id)

    def answer_callback_query(self, callback_id, text=None, **kw):
        self.outbox.append(dict(kind="answer", chat_id=None, text=text,
                                markup=None, message_id=None))

    def set_webhook(self, *a, **k):
        pass

    def remove_webhook(self, *a, **k):
        pass


telebot_mod = pytypes.ModuleType("telebot")
telebot_types = pytypes.ModuleType("telebot.types")
telebot_types.InlineKeyboardMarkup = FakeKeyboard
telebot_types.InlineKeyboardButton = FakeButton
telebot_types.Update = SimpleNamespace(de_json=staticmethod(lambda s: None))
telebot_mod.TeleBot = FakeBot
telebot_mod.types = telebot_types
sys.modules["telebot"] = telebot_mod
sys.modules["telebot.types"] = telebot_types

# --- Fake dotenv / flask / gspread / oauth2client / openai ------------------
dotenv_mod = pytypes.ModuleType("dotenv")
dotenv_mod.load_dotenv = lambda *a, **k: None
sys.modules["dotenv"] = dotenv_mod


class FakeFlask:
    def __init__(self, name):
        pass

    def route(self, path, **kw):
        def deco(fn):
            return fn
        return deco

    def run(self, *a, **k):
        pass


flask_mod = pytypes.ModuleType("flask")
flask_mod.Flask = FakeFlask
flask_mod.request = SimpleNamespace(headers={}, get_data=lambda: b"")
sys.modules["flask"] = flask_mod

gspread_mod = pytypes.ModuleType("gspread")
gspread_mod.authorize = lambda creds: (_ for _ in ()).throw(RuntimeError("offline"))
sys.modules["gspread"] = gspread_mod


class _NoCreds:
    @staticmethod
    def from_json_keyfile_name(*a, **k):
        raise FileNotFoundError("offline smoke test: no credentials.json")


oauth2client_mod = pytypes.ModuleType("oauth2client")
oauth2client_sa = pytypes.ModuleType("oauth2client.service_account")
oauth2client_sa.ServiceAccountCredentials = _NoCreds
oauth2client_mod.service_account = oauth2client_sa
sys.modules["oauth2client"] = oauth2client_mod
sys.modules["oauth2client.service_account"] = oauth2client_sa

openai_mod = pytypes.ModuleType("openai")
openai_mod.OpenAI = lambda api_key=None: SimpleNamespace()
sys.modules["openai"] = openai_mod

# --- Import the real bot code ------------------------------------------------
import main  # noqa: E402


class FakeSheet:
    def __init__(self):
        self.rows = []

    def append_row(self, row):
        self.rows.append(row)


sheet = FakeSheet()
main.planilha = sheet
bot = main.bot

# Deterministic exchange rate; individual scenarios can override.
main.buscar_cotacao_guarani = lambda cur: (1, None) if cur == "Gs" else (7300, "2026-01-01")


# --- Dispatch helpers ---------------------------------------------------------
def send_text(chat_id, text):
    msg = SimpleNamespace(
        chat=SimpleNamespace(id=chat_id, title="smoke"),
        text=text,
        message_id=1,
        voice=None,
    )
    for filters, fn in bot.message_handlers:
        content_types = filters.get("content_types")
        if content_types and "text" not in content_types:
            continue
        func = filters.get("func")
        if func and not func(msg):
            continue
        fn(msg)
        return
    raise AssertionError("no handler matched text message")


def press(chat_id, data, message_id=500):
    call = SimpleNamespace(
        id="cb",
        data=data,
        message=SimpleNamespace(chat=SimpleNamespace(id=chat_id), message_id=message_id),
    )
    start = len(bot.outbox)
    for func, fn in bot.callback_handlers:
        if func and not func(call):
            continue
        fn(call)
        answered = any(e["kind"] == "answer" for e in bot.outbox[start:])
        assert answered, f"callback {data!r} never called answer_callback_query"
        return
    raise AssertionError(f"no handler matched callback {data!r}")


def last(kind=None):
    for entry in reversed(bot.outbox):
        if kind is None or entry["kind"] == kind:
            return entry
    raise AssertionError("empty outbox")


def last_keyboard_datas():
    entry = last()
    for e in reversed(bot.outbox):
        if e["markup"] is not None:
            entry = e
            break
    return entry["markup"].callback_datas if entry["markup"] else []


FAILURES = []


def scenario(name):
    def deco(fn):
        try:
            fn()
            print(f"  PASS  {name}")
        except AssertionError as exc:
            FAILURES.append(name)
            print(f"  FAIL  {name}: {exc}")
            for e in bot.outbox[-6:]:
                print(f"        {e['kind']:6} {str(e['text'])[:90]!r}")
        return fn
    return deco


# --- Scenarios ----------------------------------------------------------------
@scenario("guided text flow saves a 10-column row")
def s1():
    send_text(1, "mcdonalds 54000")
    assert "moeda" in last()["text"].lower()
    press(1, "expense:currency:Gs")
    assert "banco" in last("edit")["text"].lower()
    press(1, "expense:banco:CONTINENTAL")
    assert "forma de pagamento" in last("edit")["text"].lower()
    press(1, "expense:forma:CREDITO")
    assert "factura" in last("edit")["text"].lower()
    press(1, "expense:factura:SI")
    assert "confirme" in last("edit")["text"].lower()
    press(1, "expense:confirm")
    assert len(sheet.rows) == 1
    row = sheet.rows[-1]
    assert len(row) == 10, f"expected 10 columns, got {len(row)}: {row}"
    assert row[0] == "MCDONALDS" and row[2] == "Gs" and row[7] == "CONTINENTAL"
    assert row[8] == "CREDITO" and row[9] == "SI"
    assert 1 not in main.pending_expenses


@scenario("EFECTIVO bank skips payment step and sets forma")
def s2():
    send_text(2, "agua 5000")
    press(2, "expense:currency:Gs")
    press(2, "expense:banco:EFECTIVO")
    assert main.pending_expenses[2]["forma"] == "EFECTIVO"
    assert "factura" in last("edit")["text"].lower(), "should ask factura, not forma"


@scenario("manual rate entry resumes at first missing field (regression: voice+EFECTIVO)")
def s3():
    main.pending_expenses[3] = dict(
        desc="AGUA DE COCO", valor=10.0, fecha="06/07/2026", moeda="BRL",
        cotizacao=None, valor_final=None, cat="ALIMENTAÇÃO",
        banco="EFECTIVO", forma="EFECTIVO", factura=None,
        stage="awaiting_exchange_rate",
    )
    send_text(3, "1300")
    text = last("edit")["text"].lower()
    assert "factura" in text, f"should skip bank+forma and ask factura, asked: {text[:80]!r}"
    assert main.pending_expenses[3]["cotizacao"] == 1300
    assert "expense:banco:CONTINENTAL" not in last_keyboard_datas(), "bank keyboard must not appear"


@scenario("continuar_apos_voz auto-fetches the rate; falls back to manual on failure")
def s4():
    main.pending_expenses[4] = dict(
        desc="TESTE", valor=10.0, fecha="06/07/2026", moeda="USD",
        cotizacao=None, valor_final=None, cat="OUTRA",
        banco=None, forma=None, factura=None, stage="voice_preview",
    )
    main.continuar_apos_voz(4, 600)
    assert main.pending_expenses[4]["cotizacao"] == 7300
    assert "banco" in last("edit")["text"].lower()

    main.pending_expenses[5] = dict(main.pending_expenses[4], cotizacao=None, valor_final=None)
    original = main.buscar_cotacao_guarani
    main.buscar_cotacao_guarani = lambda cur: (_ for _ in ()).throw(RuntimeError("api down"))
    try:
        main.continuar_apos_voz(5, 601)
    finally:
        main.buscar_cotacao_guarani = original
    assert main.pending_expenses[5]["stage"] == "awaiting_exchange_rate"
    assert "cotacao" in last("edit")["text"].lower()


@scenario("formula injection in description is neutralized before the sheet")
def s5():
    send_text(6, "=SUM(A1:A9) 5000")
    press(6, "expense:currency:Gs")
    press(6, "expense:banco:UENO")
    press(6, "expense:forma:DEBITO")
    press(6, "expense:factura:NO")
    press(6, "expense:confirm")
    row = sheet.rows[-1]
    assert row[0].startswith("'="), f"description not sanitized: {row[0]!r}"


@scenario("forged callback values are rejected")
def s6():
    send_text(7, "teste 1000")
    press(7, "expense:currency:Gs")
    press(7, "expense:banco:HACKED")
    assert main.pending_expenses[7]["banco"] is None, "invalid bank must not be stored"
    press(7, "expense:banco:CONTINENTAL")
    press(7, "expense:forma:PIX")
    assert main.pending_expenses[7]["forma"] is None, "invalid forma must not be stored"


@scenario("cancel clears pending state")
def s7():
    send_text(8, "cancelavel 2000")
    press(8, "expense:cancel")
    assert 8 not in main.pending_expenses


@scenario("Trocar forma overrides a sticky default (regression: forma inherited silently, no way to change it)")
def s8():
    send_text(9, "gasto1 1000")
    press(9, "expense:currency:Gs")
    press(9, "expense:banco:CONTINENTAL")
    press(9, "expense:forma:DEBITO")
    press(9, "expense:factura:NO")
    press(9, "expense:confirm")
    assert main.user_defaults[9]["forma"] == "DEBITO"

    send_text(9, "gasto2 2000")
    press(9, "expense:currency:Gs")
    press(9, "expense:banco:CONTINENTAL")
    assert main.pending_expenses[9]["forma"] == "DEBITO", "forma should be pre-filled from the last expense"
    assert "confirme" in last("edit")["text"].lower(), "should skip straight to confirmation"
    assert "expense:change_forma" in last_keyboard_datas(), "confirmation must offer a way to override forma"

    press(9, "expense:change_forma")
    assert "forma de pagamento" in last("edit")["text"].lower()
    assert main.pending_expenses[9]["forma"] is None
    press(9, "expense:forma:CREDITO")
    press(9, "expense:factura:NO")
    press(9, "expense:confirm")
    row = sheet.rows[-1]
    assert row[8] == "CREDITO", f"override should have saved CREDITO, got {row[8]}"


@scenario("EFECTIVO confirmation hides the forma override button")
def s9():
    send_text(10, "efectivo teste 3000")
    press(10, "expense:currency:Gs")
    press(10, "expense:banco:EFECTIVO")
    press(10, "expense:factura:NO")
    assert "confirme" in last("edit")["text"].lower()
    assert "expense:change_forma" not in last_keyboard_datas(), "cash expenses have no forma to override"
    press(10, "expense:confirm")


@scenario("Whisper transcription is biased with a bank/vocabulary prompt (regression: Meru/Auris mistranscribed)")
def s10():
    calls = []

    class FakeTranscriptions:
        def create(self, **kw):
            calls.append(kw)
            return SimpleNamespace(text="lava-jato auris cinquenta mil")

    main.openai_client = SimpleNamespace(
        audio=SimpleNamespace(transcriptions=FakeTranscriptions())
    )
    main.transcrever_audio(b"fake-ogg-bytes")
    assert calls, "transcriptions.create was not called"
    prompt = calls[0].get("prompt", "")
    assert "Meru" in prompt, f"vocabulary prompt missing bank name Meru: {prompt!r}"
    assert "Auris" in prompt, f"vocabulary prompt missing known problem word Auris: {prompt!r}"


print()
if FAILURES:
    print(f"{len(FAILURES)} scenario(s) FAILED: {', '.join(FAILURES)}")
    sys.exit(1)
print("All smoke-test scenarios passed.")
