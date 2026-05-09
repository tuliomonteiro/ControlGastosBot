import os
import telebot
from dotenv import load_dotenv
import unicodedata
from datetime import datetime
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# carregar as variaves do .env
load_dotenv()

#busca o token
TOKEN_BOT = os.getenv('TELEGRAM_TOKEN')
SHEET_KEY = os.getenv('SHEET_KEY')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://controlgastosbot.onrender.com')

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
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)

    # Abrindo a planilha pelo ID e a aba específica pelo nome
    planilha_doc = client.open_by_key(SHEET_KEY)
    planilha = planilha_doc.worksheet("2026")

    print("✅ Conexão com Google Sheets estabelecida!")
except Exception as e:
    print(f"❌ Erro na conexão com Google Sheets: {e}")

map = {
  'Mercado': ['MERCADO', 'FORTIS', 'SUPERSEIS', 'BOX', 'STOCK', 'LA MODERNA', 'SUPERMERCADO', 'LA HUERTA'],
  'Alimentação': ['ALMOÇO', 'ALMUERZO', 'JANTA', 'JANTAR', 'CENA', 'DESAYUNO', 'CAFE', 'CAFETERIA', 'CAFE DA MANHA', 'LANCHE', 'SALGADO',
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
  'Impostos': ['IMPOSTO', 'TAXA', 'SAQUE', 'IMPOSTOS']
}

BANK_OPTIONS = [
    ("CONTINENTAL", "Continental"),
    ("UENO", "Ueno"),
    ("ITAU", "Itau"),
    ("PERSONAL", "Personal"),
    ("EFETIVO", "Efetivo"),
]

PAYMENT_OPTIONS = [
    ("CREDITO", "Credito"),
    ("DEBITO", "Debito"),
]

INVOICE_OPTIONS = [
    ("SI", "Si"),
    ("NO", "No"),
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


def parse_expense_text(mensagem):
    texto = " ".join(mensagem.split())
    match = re.match(r"^(?P<desc>.+?)\s+(?P<valor>\d[\d\.,]*(?:\s*(?:k|mil))?)$", texto, re.IGNORECASE)
    if not match:
        return None

    desc = match.group("desc").strip().upper()
    valor = parse_valor_brlike(match.group("valor"))
    return desc, valor


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


def montar_resumo_gasto(expense):
    return (
        "🧾 *Confirme o gasto*\n\n"
        f"📝 *Descricao:* {expense['desc']}\n"
        f"🏷️ *Categoria:* {expense['cat']}\n"
        f"💵 *Valor:* {formatar_guaranis(expense['valor_final'])} Gs\n"
        f"🏦 *Banco:* {expense['banco']}\n"
        f"💳 *Forma:* {expense['forma']}\n"
        f"🧾 *Factura:* {expense['factura']}"
    )


def iniciar_fluxo_interativo(message, desc, valor):
    chat_id = message.chat.id
    defaults = user_defaults.get(chat_id, {})
    cat = identificar_categoria(desc, map).upper()

    pending_expenses[chat_id] = {
        "desc": desc,
        "valor": valor,
        "moeda": "Gs",
        "cotizacao": 1,
        "valor_final": valor,
        "cat": cat,
        "banco": defaults.get("banco"),
        "forma": defaults.get("forma"),
        "factura": defaults.get("factura"),
    }

    bot.reply_to(
        message,
        (
            "📝 *Novo gasto*\n\n"
            f"Descricao: {desc}\n"
            f"Valor: {formatar_guaranis(valor)} Gs\n"
            f"Categoria: {cat}\n\n"
            "Escolha o banco:"
        ),
        parse_mode="Markdown",
        reply_markup=build_keyboard(BANK_OPTIONS, "expense:banco"),
    )


def salvar_gasto(chat_id):
    expense = pending_expenses[chat_id]
    fecha = datetime.now().strftime('%d/%m/%Y')
    valor_final_format = formatar_guaranis(expense["valor_final"])

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

    user_defaults[chat_id] = {
        "banco": expense["banco"],
        "forma": expense["forma"],
        "factura": expense["factura"],
    }

    print(f"\n--- NOVO GASTO ---")
    print(f"Data: {fecha} | Cat: {expense['cat']}")
    print(f"Valor Final: {valor_final_format}")

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
    fecha = datetime.now().strftime('%d/%m/%Y')
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
        print(f"\n--- ERRO ---")
        print(f"Mensagem fora do padrão! Use 5 partes para Gs ou 7 para outras moedas.")
        print(f"Mensagem: {message.text}")
        return

    print(f"\n--- NOVO GASTO ---")
    print(f"Data: {fecha} | Cat: {cat}")
    print(f"Valor Final: {valor_final_format}")

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

    if action[1] == "forma":
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
    print(f"NOME DO CHAT: {message.chat.title} | ID: {message.chat.id}")
    # mensagem original
    mensagem_bruta = message.text

    if not mensagem_bruta:
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
                "Use o novo formato: `descricao valor`\n"
                "Exemplos: `almuerzo polka 155000` ou `almuerzo polka 155k`\n\n"
                "O formato antigo com `;` também continua funcionando."
            ),
            parse_mode="Markdown",
        )
        return

    desc, valor = parsed
    iniciar_fluxo_interativo(message, desc, valor)

if __name__ == "__main__":
    try:
        bot.remove_webhook()
    except:
        pass
    
    # Configura o webhook
    webhook_url = f"{WEBHOOK_URL}/webhook"
    bot.set_webhook(url=webhook_url)
    print(f"✅ Webhook configurado: {webhook_url}")
    
    # Inicia o servidor Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
