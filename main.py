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

# cria uma instancia do bot
bot = telebot.TeleBot(TOKEN_BOT)

# Cria uma instância do Flask para receber webhooks do Telegram
app = Flask(__name__)

@app.route('/')
def health_check():
    return {'status': 'ok', 'message': 'Bot is running'}, 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint para receber atualizações do Telegram"""
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

    cotizacao = int(round(float(rate)))
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
        expense["desc"],
        expense["valor"],
        expense["moeda"],
        expense["cotizacao"],
        valor_final_format,
        fecha,
        expense["cat"],
        expense["banco"],
        expense["forma"],
        expense["factura"],
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


@bot.callback_query_handler(func=lambda call: call.data.startswith("expense:"))
def handle_expense_callbacks(call):
    chat_id = call.message.chat.id
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
        expense["stage"] = "awaiting_payment"
        expense["banco"] = action[2]
        bot.answer_callback_query(call.id, f"Banco: {action[2]}")
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
        expense["stage"] = "awaiting_invoice"
        expense["forma"] = action[2]
        bot.answer_callback_query(call.id, f"Forma: {action[2]}")
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
        pending["stage"] = "awaiting_bank"
        bot.reply_to(
            message,
            (
                f"📈 *Cotacao registrada:* {cotizacao}\n"
                f"💵 *Valor final:* {formatar_guaranis(pending['valor_final'])} Gs\n\n"
                "Escolha o banco:"
            ),
            parse_mode="Markdown",
            reply_markup=build_keyboard(BANK_OPTIONS, "expense:banco"),
        )
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
    bot.set_webhook(url=webhook_url)
    logger.info("Webhook configurado: %s", webhook_url)
    
    # Inicia o servidor Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
