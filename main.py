import os
import logging
import telebot
from dotenv import load_dotenv
import unicodedata
from datetime import datetime
import re
import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from openai import OpenAI as OpenAIClient
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# carregar as variaves do .env
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

#busca o token
TOKEN_BOT = os.getenv('TELEGRAM_TOKEN')
SHEET_KEY = os.getenv('SHEET_KEY')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://controlgastosbot.onrender.com')
EXCHANGE_RATE_API_URL = os.getenv("EXCHANGE_RATE_API_URL", "https://api.frankfurter.dev/v1/latest")
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')
MAX_VOICE_DURATION = int(os.getenv("MAX_VOICE_DURATION", "120"))  # seconds
EXCHANGE_RATE_SPREAD = float(os.getenv("EXCHANGE_RATE_SPREAD", "1.01"))  # 1% card spread
ALLOWED_CHAT_IDS: set[int] = set(
    int(x) for x in os.getenv("ALLOWED_CHAT_IDS", "").split(",") if x.strip()
)

# cria uma instancia do bot
bot = telebot.TeleBot(TOKEN_BOT)

openai_client = OpenAIClient(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Cria uma instância do Flask para receber webhooks do Telegram
app = Flask(__name__)

@app.route('/')
def health_check():
    return {'status': 'ok', 'message': 'Bot is running'}, 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint para receber atualizações do Telegram"""
    if WEBHOOK_SECRET:
        if request.headers.get('X-Telegram-Bot-Api-Secret-Token', '') != WEBHOOK_SECRET:
            return '', 403
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return '', 403

# --- CONFIGURAÇÃO GOOGLE SHEETS ---
planilha_doc = None
planilha = None

def find_year_worksheet(doc):
    """Returns the worksheet whose title matches or contains the current year.
    Handles both 'Control de Gastos - 2026' and plain '2026' tab names."""
    year = str(datetime.now().year)
    worksheets = doc.worksheets()
    # Prefer exact match
    for ws in worksheets:
        if ws.title == year:
            return ws
    # Fall back to any tab containing the year string
    for ws in worksheets:
        if year in ws.title:
            return ws
    available = [ws.title for ws in worksheets]
    raise ValueError(f"Nenhuma aba encontrada para o ano {year}. Disponíveis: {available}")

def connect_sheets():
    global planilha_doc, planilha
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        planilha_doc = client.open_by_key(SHEET_KEY)
        planilha = find_year_worksheet(planilha_doc)
        logger.info("Conexão com Google Sheets estabelecida (aba: %s)", planilha.title)
    except Exception as e:
        logger.error("Erro na conexão com Google Sheets: %s", e)

connect_sheets()

map = {
  'Mercado': ['MERCADO', 'FORTIS', 'SUPERSEIS', 'BOX', 'STOCK', 'LA MODERNA', 'SUPERMERCADO', 'LA HUERTA'],
  'Alimentação': ['ALMOÇO','ALMOCO' ,'ALMUERZO', 'JANTA', 'JANTAR', 'CENA', 'DESAYUNO', 'CAFE', 'CAFETERIA', 'CAFE DA MANHA', 'LANCHE', 'SALGADO',
                  'BUFFET', 'CANTINA', 'CANTINA - UCP', 'RESTAURANTE', 'PIZZARIA', 'PIZZA', 'HAMBURGUER', 'HAMBURGUESA', 'LOMITO', 'FAST FOOD',
                  'MCDONALDS', 'BURGER KING', 'MOSTAZA', 'SUSHI', 'SAKURA', 'ORIGAMI', 'BELINI', 'SAN TELMO', 'DON LUIS', 'CAPITAO BAR',
                  'ARENA', 'TERRAZA', 'PANADERIA', 'BOLERIA', 'CHIPERIA', 'HELADO', 'SORVETE', 'PICOLE', 'TORTA', 'BOLO',
                  'CHOCOLATE', 'BOMBOM', 'AGUA', 'COCA', 'BEBIDA', 'MILKSHAKE', 'ALIMENTACAO'],
  'Casa':  ['DIARISTA', 'LUZ', 'AGUA', 'CASA', 'PROSEGUR', 'ALUGUEL',
            'TIGO', 'CLARO', 'BASURAS', 'ANDE', 'PERSONAL', 'ESSAP', 'ALQUILER', 'CASA'],
  'Transporte': ['ESTACIONAMENTO', 'GASOLINA', 'BOLT', 'PEDAGIOS', 'TROCA DE ACEITE', 'UBER', 'LAVAJATO', 'PEAJE', 'AURIS', 'TROCA DE OLEO', 'TRANSPORTE'],
  'Saúde': ['REMEDIOS', 'HOSPITAL', 'FARMACIA', 'SAUDE'],
  'Atividade Física': ['PILATES', 'ACADEMIA', 'PERFECT GYM', 'FISIOVERT', 'ATIVIDADE FISICA'],
  'Beleza': ['UNHA', 'DEPILACAO', 'ESFOLIANTE', 'CORTE DE CABELO', 'SOBRANCELHAS', 'PRODUTOS DE ROSTO', 'PROTETOR SOLAR', 'MANICURE', 'BELEZA'],
  'Mascota': ['PITANGA', 'RACAO', 'PETZ', 'MASCOTAS', 'MASCOTA'],
  'Assinaturas': ['1PASSWORD', 'ICLOUD', 'CHATGPT', 'GOOGLE ONE', 'AMAZON KINDLE UNLIMITED', 'AMAZON PRIME', 'SPOTIFY DUO', 'SURFSHARK VPN', 'ASSINATURA', 'ASSINATURAS'],
  'Educação': ['ITALKI', 'CURSO', 'COURSERA', 'LIVRO', 'CERTIFICACAO', 'UDEMY', 'EDUCACAO'],
  'Tecnologia': ['TECNOLOGIA'],
  'Lazer': ['KART', 'HOSPEDAGEM', 'AIRBNB', 'CORRIDA', 'LAZER', 'TIRO'],
  'Roupas': ['NIKE', 'ZARA', 'ROUPA', 'SAPATO', 'TENIS', 'ROUPAS', 'BRINCOS'],
  'Presentes': ['PRESENTE'],
  'Doações': ['DOACAO'],
  'Investimentos': ['BITCOIN'],
  'Taxas': ['TAXA', 'COMISSAO', 'TARIFA', 'TAXAS'],
  'Impostos': ['IMPOSTO', 'SAQUE', 'IMPOSTOS']
}

BANK_OPTIONS = [
    ("CONTINENTAL", "Continental"),
    ("UENO", "Ueno"),
    ("ATLAS", "Atlas"),
    ("BASA", "Basa"),
    ("MERU", "Meru"),
    ("EFECTIVO", "Efectivo"),
    ("NUBANK", "Nubank"),
    ("C6", "C6"),
    ("CORA", "Cora"),
    ("RENDIMENTO", "Rendimento"), 
]

PAYMENT_OPTIONS = [
    ("CREDITO", "Credito"),
    ("DEBITO", "Debito"),
]

INVOICE_OPTIONS = [
    ("SI", "Si"),
    ("NO", "No"),
]

CURRENCY_OPTIONS = [
    ("Gs", "Gs"),
    ("USD", "USD"),
    ("BRL", "BRL"),
    ("ARS", "ARS"),
]

VALID_BANKS = {v for v, _ in BANK_OPTIONS}
VALID_PAYMENTS = {v for v, _ in PAYMENT_OPTIONS}
VALID_INVOICES = {v for v, _ in INVOICE_OPTIONS}
VALID_CURRENCIES = {v for v, _ in CURRENCY_OPTIONS}

_FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r')

def sanitizar_celula(valor: str) -> str:
    """Prevent Google Sheets formula injection by prefixing dangerous chars."""
    if isinstance(valor, str) and valor.startswith(_FORMULA_PREFIXES):
        return "'" + valor
    return valor

def is_allowed(chat_id: int) -> bool:
    """Return True if the chat is permitted to use this bot."""
    return not ALLOWED_CHAT_IDS or chat_id in ALLOWED_CHAT_IDS

pending_expenses = {}
user_defaults = {}

def identificar_categoria(descricao, mapeamento):
    # remove acentos
    descricao_limpa = "".join(
        c for c in unicodedata.normalize('NFD', descricao)
        if unicodedata.category(c) != 'Mn'
    )
    

    for categoria, palavras in mapeamento.items():
        for palavra in palavras:
            if palavra in descricao_limpa:
                return categoria
    return "OUTRA"        


def normalizar_texto(texto):
    return "".join(
        c for c in unicodedata.normalize('NFD', texto.upper().strip())
        if unicodedata.category(c) != 'Mn'
    )


def parse_valor_brlike(valor_texto):
    valor_limpo = valor_texto.strip().lower().replace("gs", "").replace(" ", "")
    multiplicador = 1

    if valor_limpo.endswith("mil"):
        multiplicador = 1000
        valor_limpo = valor_limpo[:-3]
    elif valor_limpo.endswith("k"):
        multiplicador = 1000
        valor_limpo = valor_limpo[:-1]

    valor_limpo = valor_limpo.replace(".", "").replace(",", ".")
    valor = float(valor_limpo) * multiplicador
    return valor


def formatar_data_atual():
    return datetime.now().strftime('%d/%m/%Y')


def parse_data_texto(data_texto):
    data_limpa = data_texto.strip()
    for formato in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(data_limpa, formato).strftime("%d/%m/%Y")
        except ValueError:
            continue
    raise ValueError("Data inválida")


def parse_expense_text(mensagem):
    texto = " ".join(mensagem.split())
    match = re.match(
        r"^(?P<desc>.+?)\s+(?P<valor>\d[\d\.,]*(?:\s*(?:k|mil))?)(?:\s+(?P<fecha>\d{1,2}/\d{1,2}/(?:\d{2}|\d{4})))?$",
        texto,
        re.IGNORECASE,
    )
    if not match:
        return None

    desc = match.group("desc").strip().upper()
    valor = parse_valor_brlike(match.group("valor"))
    fecha_texto = match.group("fecha")

    try:
        fecha = parse_data_texto(fecha_texto) if fecha_texto else formatar_data_atual()
    except ValueError:
        return None

    return desc, valor, fecha


def formatar_guaranis(valor):
    return f"{valor:,.0f}".replace(",", ".")


def build_keyboard(options, prefix, row_width=2):
    keyboard = InlineKeyboardMarkup(row_width=row_width)
    buttons = [InlineKeyboardButton(label, callback_data=f"{prefix}:{value}") for value, label in options]
    keyboard.add(*buttons)
    keyboard.add(InlineKeyboardButton("Cancelar", callback_data="expense:cancel"))
    return keyboard


def build_confirmation_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Salvar", callback_data="expense:confirm"),
        InlineKeyboardButton("Cancelar", callback_data="expense:cancel"),
    )
    return keyboard


def build_exchange_rate_keyboard(currency, chat_id):
    keyboard = InlineKeyboardMarkup(row_width=1)
    last_rates = user_defaults.get(chat_id, {}).get("exchange_rates", {})
    last_rate = last_rates.get(currency)

    if last_rate:
        keyboard.add(
            InlineKeyboardButton(
                f"Usar ultima cotacao ({last_rate})",
                callback_data=f"expense:rate:{last_rate}",
            )
        )

    keyboard.add(InlineKeyboardButton("Trocar moeda", callback_data="expense:change_currency"))
    keyboard.add(InlineKeyboardButton("Cancelar", callback_data="expense:cancel"))
    return keyboard


def buscar_cotacao_guarani(currency):
    if currency == "Gs":
        return 1, None

    url = f"{EXCHANGE_RATE_API_URL}?base={currency}&symbols=PYG"

    try:
        with urlopen(url, timeout=5) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"Falha ao consultar cotacao para {currency}: {exc}") from exc

    rates = payload.get("rates", {})
    rate = rates.get("PYG")
    if rate is None:
        raise RuntimeError(f"Resposta sem taxa PYG para {currency}.")

    cotizacao = int(round(float(rate) * EXCHANGE_RATE_SPREAD))
    if cotizacao <= 0:
        raise RuntimeError(f"Cotacao invalida recebida para {currency}: {rate}")

    return cotizacao, payload.get("date")


def montar_resumo_gasto(expense):
    resumo = (
        "🧾 *Confirme o gasto*\n\n"
        f"📝 *Descricao:* {expense['desc']}\n"
        f"🏷️ *Categoria:* {expense['cat']}\n"
    )

    if expense["moeda"] == "Gs":
        resumo += f"💵 *Valor:* {formatar_guaranis(expense['valor_final'])} Gs\n"
    else:
        resumo += (
            f"💰 *Origem:* {expense['moeda']} {expense['valor']}\n"
            f"📈 *Cotacao:* {expense['cotizacao']}\n"
            f"💵 *Final:* {formatar_guaranis(expense['valor_final'])} Gs\n"
        )

    resumo += (
        f"📅 *Data:* {expense['fecha']}\n"
        f"🏦 *Banco:* {expense['banco']}\n"
        f"💳 *Forma:* {expense['forma']}\n"
        f"🧾 *Factura:* {expense['factura']}"
    )
    return resumo


def pedir_banco(chat_id, message_id):
    expense = pending_expenses[chat_id]
    bot.edit_message_text(
        (
            "🏦 *Escolha o banco*\n\n"
            f"Descricao: {expense['desc']}\n"
            f"Valor final: {formatar_guaranis(expense['valor_final'])} Gs\n"
            f"Categoria: {expense['cat']}"
        ),
        chat_id=chat_id,
        message_id=message_id,
        parse_mode="Markdown",
        reply_markup=build_keyboard(BANK_OPTIONS, "expense:banco"),
    )


def pedir_cotacao_manual(chat_id, message_id):
    expense = pending_expenses[chat_id]
    bot.edit_message_text(
        (
            "📈 *Informe a cotacao do dia*\n\n"
            f"Descricao: {expense['desc']}\n"
            f"Valor original: {expense['moeda']} {expense['valor']}\n\n"
            "Tentei buscar a cotacao automaticamente, mas voce ainda pode:\n"
            "- enviar a cotacao manualmente\n"
            "- usar a ultima cotacao salva\n\n"
            "Envie apenas o numero da cotacao.\n"
            "Exemplo: `1254`"
        ),
        chat_id=chat_id,
        message_id=message_id,
        parse_mode="Markdown",
        reply_markup=build_exchange_rate_keyboard(expense["moeda"], chat_id),
    )


def pedir_forma(chat_id, message_id):
    expense = pending_expenses[chat_id]
    bot.edit_message_text(
        (
            "💳 *Escolha a forma de pagamento*\n\n"
            f"Descricao: {expense['desc']}\n"
            f"Valor: {formatar_guaranis(expense['valor_final'])} Gs\n"
            f"Banco: {expense['banco']}"
        ),
        chat_id=chat_id,
        message_id=message_id,
        parse_mode="Markdown",
        reply_markup=build_keyboard(PAYMENT_OPTIONS, "expense:forma"),
    )


def pedir_factura(chat_id, message_id):
    expense = pending_expenses[chat_id]
    bot.edit_message_text(
        (
            "🧾 *Tem factura?*\n\n"
            f"Descricao: {expense['desc']}\n"
            f"Valor: {formatar_guaranis(expense['valor_final'])} Gs\n"
            f"Banco: {expense['banco']}\n"
            f"Forma: {expense['forma']}"
        ),
        chat_id=chat_id,
        message_id=message_id,
        parse_mode="Markdown",
        reply_markup=build_keyboard(INVOICE_OPTIONS, "expense:factura"),
    )


def build_voice_save_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Salvar", callback_data="voice:save_all"),
        InlineKeyboardButton("🔄 Corrigir", callback_data="voice:retry"),
    )
    keyboard.add(InlineKeyboardButton("❌ Cancelar", callback_data="expense:cancel"))
    return keyboard


def continuar_apos_voz(chat_id, message_id):
    """Resume from the first missing field after voice confirmation."""
    expense = pending_expenses[chat_id]

    if expense.get("cotizacao") is None and expense["moeda"] != "Gs":
        try:
            cotizacao, _ = buscar_cotacao_guarani(expense["moeda"])
            expense["cotizacao"] = cotizacao
            expense["valor_final"] = expense["valor"] * cotizacao
        except RuntimeError:
            expense["stage"] = "awaiting_exchange_rate"
            pedir_cotacao_manual(chat_id, message_id)
            return

    if expense.get("banco") is None:
        expense["stage"] = "awaiting_bank"
        pedir_banco(chat_id, message_id)
    elif expense.get("forma") is None:
        expense["stage"] = "awaiting_payment"
        pedir_forma(chat_id, message_id)
    elif expense.get("factura") is None:
        expense["stage"] = "awaiting_invoice"
        pedir_factura(chat_id, message_id)
    else:
        expense["stage"] = "awaiting_confirmation"
        bot.edit_message_text(
            montar_resumo_gasto(expense),
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown",
            reply_markup=build_confirmation_keyboard(),
        )


def iniciar_fluxo_interativo(message, desc, valor, fecha):
    chat_id = message.chat.id
    defaults = user_defaults.get(chat_id, {})
    cat = identificar_categoria(desc, map).upper()

    pending_expenses[chat_id] = {
        "desc": desc,
        "valor": valor,
        "fecha": fecha,
        "moeda": None,
        "cotizacao": None,
        "valor_final": None,
        "cat": cat,
        "banco": defaults.get("banco"),
        "forma": defaults.get("forma"),
        "factura": defaults.get("factura"),
        "stage": "awaiting_currency",
    }

    bot.reply_to(
        message,
        (
            "📝 *Novo gasto*\n\n"
            f"Descricao: {desc}\n"
            f"Categoria: {cat}\n\n"
            f"Data: {fecha}\n"
            f"Valor informado: {valor}\n\n"
            "Qual a moeda da compra?"
        ),
        parse_mode="Markdown",
        reply_markup=build_keyboard(CURRENCY_OPTIONS, "expense:currency"),
    )


def salvar_gasto(chat_id):
    expense = pending_expenses[chat_id]
    fecha = expense["fecha"]
    valor_final_format = formatar_guaranis(expense["valor_final"])
    defaults = user_defaults.get(chat_id, {})
    exchange_rates = defaults.get("exchange_rates", {})

    dados_linha = [
        sanitizar_celula(expense["desc"]),
        expense["valor"],
        expense["moeda"],
        expense["cotizacao"],
        valor_final_format,
        fecha,
        sanitizar_celula(expense["cat"]),
        sanitizar_celula(expense["banco"]),
        sanitizar_celula(expense["forma"]),
        sanitizar_celula(expense["factura"]),
    ]
    planilha.append_row(dados_linha)

    if expense["moeda"] != "Gs":
        exchange_rates[expense["moeda"]] = expense["cotizacao"]

    user_defaults[chat_id] = {
        "banco": expense["banco"],
        "forma": expense["forma"],
        "factura": expense["factura"],
        "exchange_rates": exchange_rates,
    }

    logger.info("Gasto salvo | Data: %s | Cat: %s | Valor: %s Gs", fecha, expense['cat'], valor_final_format)

    del pending_expenses[chat_id]

    return (
        "✅ *Gasto registrado!*\n\n"
        f"📝 *Descrição:* {expense['desc']}\n"
        f"🏷️ *Categoria:* {expense['cat']}\n"
        f"💵 *Valor:* {valor_final_format} Gs\n"
        f"📅 *Data:* {fecha}\n"
        f"🏦 *Banco:* {expense['banco']}\n"
        f"💳 *Forma:* {expense['forma']}\n"
        f"🧾 *Factura:* {expense['factura']}"
    )


def processar_formato_legado(message, partes):
    #identificacao da data
    fecha = formatar_data_atual()
    mensagem_resposta = ""

    # Se for guarani
    if len(partes) == 5:
        desc = partes[0].upper()
        cat = identificar_categoria(desc, map).upper()
        valor = float(partes[1].replace('.', '').replace(',', '.'))
        moeda = "Gs"
        cotizacao = 1
        valor_final = valor * cotizacao
        banco_bruto = partes[2].upper().strip()
        banco = "".join(c for c in unicodedata.normalize('NFD', banco_bruto) if unicodedata.category(c) != 'Mn')
        forma_bruta = partes[3].upper().strip()
        forma = "".join(c for c in unicodedata.normalize('NFD', forma_bruta) if unicodedata.category(c) != 'Mn')
        factura = partes[4].upper()

        valor_final_format = formatar_guaranis(valor_final)

        dados_linha = [desc, valor, moeda, cotizacao, valor_final_format,
                        fecha, cat, banco, forma, factura]
        planilha.append_row(dados_linha)

        user_defaults[message.chat.id] = {
            "banco": banco,
            "forma": forma,
            "factura": factura,
        }

        mensagem_resposta = f"""
        ✅ *Gasto registrado!*

        📝 *Descrição:* {desc}
        🏷️ *Categoria:* {cat}
        💵 *Valor:* {valor_final_format} Gs
        📅 *Data:* {fecha}
        🏦 *Banco:* {banco}
        💳 *Forma:* {forma}
        🧾 *Factura:* {factura}
        """

    # Outra moeda
    elif len(partes) == 7:
        desc = partes[0].upper()
        cat = identificar_categoria(desc, map).upper()
        moeda = partes[1].upper()
        valor = float(partes[2].replace('.', '').replace(',', '.'))
        cotizacao = int(partes[3].replace('.', '').replace(',', '.'))
        valor_final = valor * cotizacao
        banco_bruto = partes[4].upper().strip()
        banco = "".join(c for c in unicodedata.normalize('NFD', banco_bruto) if unicodedata.category(c) != 'Mn')
        forma_bruta = partes[5].upper().strip()
        forma = "".join(c for c in unicodedata.normalize('NFD', forma_bruta) if unicodedata.category(c) != 'Mn')
        factura = partes[6].upper()

        valor_final_format = formatar_guaranis(valor_final)

        dados_linha = [desc, valor, moeda, cotizacao, valor_final_format,
                        fecha, cat, banco, forma, factura]
        planilha.append_row(dados_linha)

        user_defaults[message.chat.id] = {
            "banco": banco,
            "forma": forma,
            "factura": factura,
        }

        mensagem_resposta = f"""
        ✅ *Gasto registrado!*
        
        📝 *Descrição:* {desc}
        🏷️ *Categoria:* {cat}
        💰 *Origem:* {moeda} {valor}
        📈 *Cotação:* {cotizacao}
        💵 *Final:* {valor_final_format} Gs
        📅 *Data:* {fecha}
        🏦 *Banco:* {banco}
        💳 *Forma:* {forma}
        🧾 *Factura:* {factura}"""

    else:
        bot.reply_to(message, "❌ Mensagem fora do padrão! Use 5 partes para Gs ou 7 para outras moedas.")
        logger.warning("Formato legado inválido: %s", message.text)
        return

    logger.info("Gasto salvo (legado) | Data: %s | Cat: %s | Valor: %s Gs", fecha, cat, valor_final_format)

    bot.reply_to(message, mensagem_resposta, parse_mode="Markdown")


def transcrever_audio(file_content: bytes) -> str:
    transcript = openai_client.audio.transcriptions.create(
        model="whisper-1",
        file=("audio.ogg", file_content, "audio/ogg"),
        language="pt",
    )
    return transcript.text


def extrair_gasto_do_texto(transcript: str) -> dict:
    hoje = formatar_data_atual()
    bancos = ", ".join(VALID_BANKS)
    prompt = (
        f'Extraia as informações do gasto deste texto em português brasileiro.\n\n'
        f'Texto: "{transcript}"\n\n'
        f'Data de hoje: {hoje}\n\n'
        'Retorne um JSON com os campos:\n'
        '- "desc": descrição em MAIÚSCULAS (string)\n'
        '- "valor": valor numérico sem formatação (number)\n'
        '- "moeda": exatamente "Gs", "USD", "BRL" ou "ARS" (padrão "Gs" se não mencionado)\n'
        f'- "banco": um dos valores exatos [{bancos}] ou null se não mencionado\n'
        '- "forma": exatamente "CREDITO" ou "DEBITO" ou null se não mencionado\n'
        '- "factura": exatamente "SI" ou "NO" ou null se não mencionado\n'
        f'- "fecha": data no formato DD/MM/AAAA (use {hoje} se não mencionada)\n\n'
        'Regras de normalização:\n'
        '"crédito"/"no crédito"/"credit" → forma "CREDITO"\n'
        '"débito"/"no débito" → forma "DEBITO"\n'
        '"com factura"/"com nota"/"com fatura" → factura "SI"\n'
        '"sem factura"/"sem nota"/"sem fatura" → factura "NO"\n'
        '"guaranis"/"guaranies"/"Gs" → moeda "Gs"\n'
        '"reais"/"real"/"BRL" → moeda "BRL"\n'
        '"dólares"/"dolares"/"USD" → moeda "USD"\n'
        '"efectivo"/"dinheiro"/"em dinheiro"/"pagamento em dinheiro"/"cash" → banco "EFECTIVO"\n'
        'Responda APENAS com o JSON.'
    )
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(response.choices[0].message.content)


def build_voice_confirmation_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Confirmar", callback_data="voice:confirm"),
        InlineKeyboardButton("🔄 Tentar de novo", callback_data="voice:retry"),
    )
    keyboard.add(InlineKeyboardButton("❌ Cancelar", callback_data="expense:cancel"))
    return keyboard


@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    chat_id = message.chat.id

    if not is_allowed(chat_id):
        return

    if not openai_client:
        bot.reply_to(message, "❌ Reconhecimento de voz não configurado. Defina OPENAI_API_KEY.")
        return

    if message.voice.duration > MAX_VOICE_DURATION:
        bot.reply_to(
            message,
            f"❌ Áudio muito longo ({message.voice.duration}s). Máximo: {MAX_VOICE_DURATION}s.",
        )
        return

    processing_msg = bot.reply_to(message, "🎤 Processando áudio...")

    try:
        file_info = bot.get_file(message.voice.file_id)
        file_content = bot.download_file(file_info.file_path)

        transcript = transcrever_audio(file_content)
        logger.info("Transcrição de voz | Chat: %s | Texto: %s", chat_id, transcript)

        gasto = extrair_gasto_do_texto(transcript)

        desc = str(gasto.get("desc", "")).upper().strip()
        valor = float(gasto.get("valor", 0))
        moeda = str(gasto.get("moeda", "Gs"))
        fecha = str(gasto.get("fecha", formatar_data_atual()))
        banco = str(gasto.get("banco") or "").upper().strip() or None
        forma = str(gasto.get("forma") or "").upper().strip() or None
        factura = str(gasto.get("factura") or "").upper().strip() or None

        if moeda not in VALID_CURRENCIES:
            moeda = "Gs"
        if banco not in VALID_BANKS:
            banco = None
        if banco == "EFECTIVO":
            forma = "EFECTIVO"
        elif forma not in VALID_PAYMENTS:
            forma = None
        if factura not in VALID_INVOICES:
            factura = None

        if not desc or valor <= 0:
            bot.edit_message_text(
                "❌ Não consegui identificar o gasto. Tente novamente ou use o formato de texto.",
                chat_id=chat_id,
                message_id=processing_msg.message_id,
            )
            return

        cat = identificar_categoria(desc, map).upper()

        # Resolve exchange rate immediately (with spread)
        cotizacao = None
        valor_final = None
        rate_note = ""
        if moeda == "Gs":
            cotizacao = 1
            valor_final = valor
        else:
            try:
                cotizacao, rate_date = buscar_cotacao_guarani(moeda)
                valor_final = valor * cotizacao
                rate_note = f" (+1% spread, ref. {rate_date})" if rate_date else " (+1% spread)"
            except RuntimeError:
                pass  # will ask for rate later in the flow

        expense = {
            "desc": desc,
            "valor": valor,
            "fecha": fecha,
            "moeda": moeda,
            "cotizacao": cotizacao,
            "valor_final": valor_final,
            "cat": cat,
            "banco": banco,
            "forma": forma,
            "factura": factura,
            "stage": "voice_preview",
        }
        pending_expenses[chat_id] = expense

        all_complete = all([banco, forma, factura, valor_final is not None])

        if moeda == "Gs":
            valor_display = f"{formatar_guaranis(valor)} Gs"
        elif valor_final is not None:
            valor_display = f"{moeda} {valor} → {formatar_guaranis(valor_final)} Gs{rate_note}"
        else:
            valor_display = f"{moeda} {valor} (cotação pendente)"

        if all_complete:
            expense["stage"] = "voice_full_preview"
            resumo = (
                "🎤 *Confirme o gasto:*\n\n"
                f"🗣️ _{transcript}_\n\n"
                f"📝 *Descrição:* {desc}\n"
                f"🏷️ *Categoria:* {cat}\n"
                f"💵 *Valor:* {valor_display}\n"
                f"📅 *Data:* {fecha}\n"
                f"🏦 *Banco:* {banco}\n"
                f"💳 *Forma:* {forma}\n"
                f"🧾 *Factura:* {factura}"
            )
            bot.edit_message_text(
                resumo,
                chat_id=chat_id,
                message_id=processing_msg.message_id,
                parse_mode="Markdown",
                reply_markup=build_voice_save_keyboard(),
            )
        else:
            resumo = (
                "🎤 *Eu entendi:*\n\n"
                f"🗣️ _{transcript}_\n\n"
                f"📝 *Descrição:* {desc}\n"
                f"🏷️ *Categoria:* {cat}\n"
                f"💵 *Valor:* {valor_display}\n"
                f"📅 *Data:* {fecha}\n"
            )
            if banco:
                resumo += f"🏦 *Banco:* {banco}\n"
            if forma:
                resumo += f"💳 *Forma:* {forma}\n"
            if factura:
                resumo += f"🧾 *Factura:* {factura}\n"
            resumo += "\nConfirmar e preencher campos restantes?"
            bot.edit_message_text(
                resumo,
                chat_id=chat_id,
                message_id=processing_msg.message_id,
                parse_mode="Markdown",
                reply_markup=build_voice_confirmation_keyboard(),
            )

    except Exception as e:
        logger.exception("Erro no reconhecimento de voz")
        bot.edit_message_text(
            f"❌ Erro ao processar o áudio: `{type(e).__name__}: {e}`\n\nTente novamente.",
            chat_id=chat_id,
            message_id=processing_msg.message_id,
            parse_mode="Markdown",
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("voice:"))
def handle_voice_callbacks(call):
    chat_id = call.message.chat.id
    if not is_allowed(chat_id):
        bot.answer_callback_query(call.id)
        return
    action = call.data.split(":", 1)[1]

    if action == "retry":
        pending_expenses.pop(chat_id, None)
        bot.answer_callback_query(call.id, "Envie o áudio novamente.")
        bot.edit_message_text(
            "🎤 Por favor, envie o áudio novamente.",
            chat_id=chat_id,
            message_id=call.message.message_id,
        )
        return

    if action == "save_all":
        expense = pending_expenses.get(chat_id)
        if not expense:
            bot.answer_callback_query(call.id, "Nenhum gasto pendente.")
            return
        bot.answer_callback_query(call.id, "Salvando...")
        mensagem = salvar_gasto(chat_id)
        bot.edit_message_text(
            mensagem,
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
        )
        return

    if action == "confirm":
        expense = pending_expenses.get(chat_id)
        if not expense:
            bot.answer_callback_query(call.id, "Nenhum gasto pendente.")
            return
        bot.answer_callback_query(call.id, "Confirmado!")
        continuar_apos_voz(chat_id, call.message.message_id)
        return

    bot.answer_callback_query(call.id, "Ação não reconhecida.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("expense:"))
def handle_expense_callbacks(call):
    chat_id = call.message.chat.id
    if not is_allowed(chat_id):
        bot.answer_callback_query(call.id)
        return
    expense = pending_expenses.get(chat_id)

    if call.data == "expense:cancel":
        pending_expenses.pop(chat_id, None)
        bot.answer_callback_query(call.id, "Lançamento cancelado.")
        bot.edit_message_text(
            "❌ Lançamento cancelado.",
            chat_id=chat_id,
            message_id=call.message.message_id,
        )
        return

    if not expense:
        bot.answer_callback_query(call.id, "Nenhum gasto pendente.")
        return

    action = call.data.split(":", 2)
    if len(action) < 2:
        bot.answer_callback_query(call.id, "Ação inválida.")
        return

    if action[1] == "banco":
        if action[2] not in VALID_BANKS:
            bot.answer_callback_query(call.id, "Banco inválido.")
            return
        expense["banco"] = action[2]
        bot.answer_callback_query(call.id, f"Banco: {action[2]}")

        if expense["banco"] == "EFECTIVO":
            expense["forma"] = "EFECTIVO"
            if expense.get("factura") is not None:
                expense["stage"] = "awaiting_confirmation"
                bot.edit_message_text(
                    montar_resumo_gasto(expense),
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    parse_mode="Markdown",
                    reply_markup=build_confirmation_keyboard(),
                )
            else:
                expense["stage"] = "awaiting_invoice"
                pedir_factura(chat_id, call.message.message_id)
            return

        # Skip forma if already captured (e.g. from voice)
        if expense.get("forma") is not None:
            if expense.get("factura") is not None:
                expense["stage"] = "awaiting_confirmation"
                bot.edit_message_text(
                    montar_resumo_gasto(expense),
                    chat_id=chat_id,
                    message_id=call.message.message_id,
                    parse_mode="Markdown",
                    reply_markup=build_confirmation_keyboard(),
                )
            else:
                expense["stage"] = "awaiting_invoice"
                pedir_factura(chat_id, call.message.message_id)
            return

        expense["stage"] = "awaiting_payment"
        bot.edit_message_text(
            (
                "💳 *Escolha a forma de pagamento*\n\n"
                f"Descricao: {expense['desc']}\n"
                f"Valor: {formatar_guaranis(expense['valor_final'])} Gs\n"
                f"Banco: {expense['banco']}"
            ),
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
            reply_markup=build_keyboard(PAYMENT_OPTIONS, "expense:forma"),
        )
        return

    if action[1] == "currency":
        if action[2] not in VALID_CURRENCIES:
            bot.answer_callback_query(call.id, "Moeda inválida.")
            return
        expense["moeda"] = action[2]
        if expense["moeda"] == "Gs":
            expense["cotizacao"] = 1
            expense["valor_final"] = expense["valor"]
            expense["stage"] = "awaiting_bank"
            bot.answer_callback_query(call.id, "Moeda: Gs")
            pedir_banco(chat_id, call.message.message_id)
            return

        expense["stage"] = "awaiting_exchange_rate"
        bot.answer_callback_query(call.id, f"Moeda: {expense['moeda']}")
        try:
            cotizacao, data_cotacao = buscar_cotacao_guarani(expense["moeda"])
        except RuntimeError as exc:
            logger.warning("Falha ao buscar cotação automática: %s", exc)
            pedir_cotacao_manual(chat_id, call.message.message_id)
            return

        expense["cotizacao"] = cotizacao
        expense["valor_final"] = expense["valor"] * cotizacao
        expense["stage"] = "awaiting_bank"
        data_msg = f"\n📅 *Data da API:* {data_cotacao}" if data_cotacao else ""
        bot.edit_message_text(
            (
                "🤖 *Cotacao obtida automaticamente*\n\n"
                f"Descricao: {expense['desc']}\n"
                f"Valor original: {expense['moeda']} {expense['valor']}\n"
                f"📈 *Cotacao usada:* {cotizacao}{data_msg}\n"
                f"💵 *Valor final:* {formatar_guaranis(expense['valor_final'])} Gs\n\n"
                "Escolha o banco:"
            ),
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
            reply_markup=build_keyboard(BANK_OPTIONS, "expense:banco"),
        )
        return

    if action[1] == "change_currency":
        expense["stage"] = "awaiting_currency"
        expense["moeda"] = None
        expense["cotizacao"] = None
        expense["valor_final"] = None
        bot.answer_callback_query(call.id, "Escolha outra moeda.")
        bot.edit_message_text(
            (
                "💱 *Qual a moeda da compra?*\n\n"
                f"Descricao: {expense['desc']}\n"
                f"Valor informado: {expense['valor']}"
            ),
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
            reply_markup=build_keyboard(CURRENCY_OPTIONS, "expense:currency"),
        )
        return

    if action[1] == "rate":
        cotizacao = int(action[2])
        expense["cotizacao"] = cotizacao
        expense["valor_final"] = expense["valor"] * cotizacao
        expense["stage"] = "awaiting_bank"
        bot.answer_callback_query(call.id, f"Cotacao: {cotizacao}")
        pedir_banco(chat_id, call.message.message_id)
        return

    if action[1] == "forma":
        if action[2] not in VALID_PAYMENTS:
            bot.answer_callback_query(call.id, "Forma de pagamento inválida.")
            return
        expense["forma"] = action[2]
        bot.answer_callback_query(call.id, f"Forma: {action[2]}")
        # Skip factura if already captured (e.g. from voice)
        if expense.get("factura") is not None:
            expense["stage"] = "awaiting_confirmation"
            bot.edit_message_text(
                montar_resumo_gasto(expense),
                chat_id=chat_id,
                message_id=call.message.message_id,
                parse_mode="Markdown",
                reply_markup=build_confirmation_keyboard(),
            )
        else:
            expense["stage"] = "awaiting_invoice"
            bot.edit_message_text(
                (
                    "🧾 *Tem factura?*\n\n"
                    f"Descricao: {expense['desc']}\n"
                    f"Valor: {formatar_guaranis(expense['valor_final'])} Gs\n"
                    f"Banco: {expense['banco']}\n"
                    f"Forma: {expense['forma']}"
                ),
                chat_id=chat_id,
                message_id=call.message.message_id,
                parse_mode="Markdown",
                reply_markup=build_keyboard(INVOICE_OPTIONS, "expense:factura"),
            )
        return

    if action[1] == "factura":
        if action[2] not in VALID_INVOICES:
            bot.answer_callback_query(call.id, "Opção de factura inválida.")
            return
        expense["stage"] = "awaiting_confirmation"
        expense["factura"] = action[2]
        bot.answer_callback_query(call.id, f"Factura: {action[2]}")
        bot.edit_message_text(
            montar_resumo_gasto(expense),
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
            reply_markup=build_confirmation_keyboard(),
        )
        return

    if action[1] == "confirm":
        mensagem = salvar_gasto(chat_id)
        bot.answer_callback_query(call.id, "Gasto salvo.")
        bot.edit_message_text(
            mensagem,
            chat_id=chat_id,
            message_id=call.message.message_id,
            parse_mode="Markdown",
        )
        return

    bot.answer_callback_query(call.id, "Ação não reconhecida.")

# --- HANDLER 2: OUVINTE GERAL (FINANÇAS) ---
@bot.message_handler(func=lambda message: True)
def processar_gastos(message):
    if not is_allowed(message.chat.id):
        return
    logger.info("Mensagem recebida | Chat: %s | ID: %s", message.chat.title, message.chat.id)
    # mensagem original
    mensagem_bruta = message.text

    if not mensagem_bruta:
        return

    pending = pending_expenses.get(message.chat.id)
    if pending and pending.get("stage") == "awaiting_exchange_rate":
        try:
            cotizacao = int(parse_valor_brlike(mensagem_bruta))
        except ValueError:
            bot.reply_to(
                message,
                "❌ Cotação inválida. Envie apenas o número, por exemplo: `1254`",
                parse_mode="Markdown",
            )
            return

        pending["cotizacao"] = cotizacao
        pending["valor_final"] = pending["valor"] * cotizacao

        rate_msg = bot.reply_to(
            message,
            (
                f"📈 *Cotação registrada:* {cotizacao}\n"
                f"💵 *Valor final:* {formatar_guaranis(pending['valor_final'])} Gs"
            ),
            parse_mode="Markdown",
        )
        continuar_apos_voz(message.chat.id, rate_msg.message_id)
        return

    if ";" in mensagem_bruta:
        partes = [" ".join(p.split()) for p in mensagem_bruta.split(';')]
        processar_formato_legado(message, partes)
        return

    parsed = parse_expense_text(mensagem_bruta)
    if not parsed:
        bot.reply_to(
            message,
            (
                "❌ Não entendi a mensagem.\n\n"
                "Use o novo formato: `descricao valor` ou `descricao valor data`\n"
                "Exemplos: `almuerzo polka 155000`, `almuerzo polka 155k` ou `mcdonalds 54000 09/06/26`\n\n"
                "O formato antigo com `;` também continua funcionando."
            ),
            parse_mode="Markdown",
        )
        return

    desc, valor, fecha = parsed
    iniciar_fluxo_interativo(message, desc, valor, fecha)

if __name__ == "__main__":
    try:
        bot.remove_webhook()
    except:
        pass
    
    # Configura o webhook
    webhook_url = f"{WEBHOOK_URL}/webhook"
    bot.set_webhook(url=webhook_url, secret_token=WEBHOOK_SECRET or None)
    logger.info("Webhook configurado: %s", webhook_url)
    
    # Inicia o servidor Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
