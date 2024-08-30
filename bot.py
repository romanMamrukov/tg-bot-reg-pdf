import json
import os
import re
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext, CallbackQueryHandler
from telegram.constants import ParseMode

# Define states for the conversation
LANGUAGE, FIRST_NAME, LAST_NAME, EMAIL, CUST_AMOUNT = range(5)

# File path to store user data
DATA_FILE = "user_data.json" # Your user data file

# Load existing user data from file
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, 'r') as file:
            user_data = json.load(file)
    except json.JSONDecodeError:
        user_data = {}
else:
    user_data = {}

# Language translation dictionary
translations = {
    "en": {
        "start": "Hello! I'm 'Name' bot. I can help you with registration and retrieve your previous registrations.\n\nUse /register to start a new registration or /retrieve to view your previous registrations.",
        "select_language": "Please select your preferred language:",
        "register": "Let's start with your registration. What's your first name?",
        "ask_first_name": "Great! Now, what's your surname?",
        "ask_last_name": "Perfect! Can you provide your email address?",
        "ask_email": "Thanks! How many people will be attending?",
        "thank_you": "Thank you for the information! Here's a summary of your registration:",
        "invalid_number": "Please enter a valid number for the number of people.",
        "retrieve": "Here are your previous registrations:\n\n",
        "no_registrations": "You have no previous registrations.",
        "first_name": "First Name",
        "last_name": "Last Name",
        "email": "Email",
        "number_of_people": "Number of People",
        "new_registration": "New Registration",
        "pdf_invoice": "Invoice PDF",
    },
    "lv": {
        "start": "Sveiki! Es esmu 'Vards' bots. Es varu jums palīdzēt ar reģistrāciju un atgūt jūsu iepriekšējās reģistrācijas.\n\nIzmantojiet /register, lai sāktu jaunu reģistrāciju, vai /retrieve, lai apskatītu jūsu iepriekšējās reģistrācijas.",
        "select_language": "Lūdzu, izvēlieties vēlamo valodu:",
        "register": "Sāksim ar jūsu reģistrāciju. Kāds ir jūsu vārds?",
        "ask_first_name": "Lieliski! Kāds ir jūsu uzvārds?",
        "ask_last_name": "Perfekti! Vai varat norādīt savu e-pasta adresi?",
        "ask_email": "Paldies! Cik cilvēki piedalīsies?",
        "thank_you": "Paldies par informāciju! Šeit ir jūsu reģistrācijas kopsavilkums:",
        "invalid_number": "Lūdzu, ievadiet derīgu cilvēku skaitu.",
        "retrieve": "Šeit ir jūsu iepriekšējās reģistrācijas:\n\n",
        "no_registrations": "Jums nav iepriekšēju reģistrāciju.",
        "first_name": "Vārds",
        "last_name": "Uzvārds",
        "email": "E-pasts",
        "number_of_people": "Cilvēku skaits",
        "new_registration": "Jauna reģistrācija",
        "pdf_invoice": "Rēķins PDF formātā",
    },
    "ru": {
        "start": "Привет! Я бот 'Имя''. Я могу помочь вам с регистрацией и получить ваши предыдущие регистрации.\n\nИспользуйте /register, чтобы начать новую регистрацию, или /retrieve, чтобы просмотреть ваши предыдущие регистрации.",
        "select_language": "Пожалуйста, выберите предпочитаемый язык:",
        "register": "Начнем с вашей регистрации. Как ваше имя?",
        "ask_first_name": "Отлично! Как ваша фамилия?",
        "ask_last_name": "Прекрасно! Можете указать свой адрес электронной почты?",
        "ask_email": "Спасибо! Сколько человек будет присутствовать?",
        "thank_you": "Спасибо за информацию! Вот сводка вашей регистрации:",
        "invalid_number": "Пожалуйста, введите действительное количество человек.",
        "retrieve": "Вот ваши предыдущие регистрации:\n\n",
        "no_registrations": "У вас нет предыдущих регистраций.",
        "first_name": "Имя",
        "last_name": "Фамилия",
        "email": "Электронная почта",
        "number_of_people": "Количество человек",
        "new_registration": "Новая регистрация",
        "pdf_invoice": "PDF-счет",
    }
}

# Function to retrieve the translation
def t(key: str, lang: str = 'en') -> str:
    return translations.get(lang, translations['en']).get(key, key)

async def start(update: Update, context: CallbackContext) -> int:
    keyboard = [
        [InlineKeyboardButton("Latviešu", callback_data='lv')],
        [InlineKeyboardButton("Русский", callback_data='ru')],
        [InlineKeyboardButton("English", callback_data='en')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(t("select_language"), reply_markup=reply_markup)
    return LANGUAGE  # Transition to LANGUAGE state

async def select_language(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    user_id = str(query.from_user.id)
    lang = query.data

    # Store user's language choice
    user_data.setdefault(user_id, []).append({'lang': lang})
    await query.answer()
    await query.edit_message_text(t("register", lang))
    return FIRST_NAME  # Transition to FIRST_NAME state

async def ask_first_name(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    first_name = update.message.text

    # Store the user's first name
    user_data[user_id][-1]['first_name'] = first_name

    await update.message.reply_text(t("ask_first_name", lang))
    return LAST_NAME  # Transition to LAST_NAME state

async def ask_last_name(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    last_name = update.message.text

    # Store the user's surname
    user_data[user_id][-1]['last_name'] = last_name

    await update.message.reply_text(t("ask_last_name", lang))
    return EMAIL  # Transition to EMAIL state

async def ask_email(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    email = update.message.text

    # Store the user's email
    user_data[user_id][-1]['email'] = email

    await update.message.reply_text(t("ask_email", lang))
    return CUST_AMOUNT  # Transition to CUST_AMOUNT state

async def ask_cust_amount(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    try:
        cust_amount = int(update.message.text)
        user_data[user_id][-1]['cust_amount'] = cust_amount

        # Save user data to the file only after the registration is completed
        with open(DATA_FILE, 'w') as file:
            json.dump(user_data, file)

        # Generate and send the registration summary
        user_info = user_data[user_id][-1]
        summary = (
            f"{t('first_name', lang)}: {user_info.get('first_name', 'Unknown')}\n"
            f"{t('last_name', lang)}: {user_info.get('last_name', 'Unknown')}\n"
            f"{t('email', lang)}: {user_info.get('email', 'Unknown')}\n"
            f"{t('number_of_people', lang)}: {cust_amount}"
        )

        await update.message.reply_text(t("thank_you", lang))
        await update.message.reply_text(summary)

        # Send the summary to the specified channel
        await context.bot.send_message(chat_id="@Channel_ID", text=f"{t('new_registration', lang)}:\n\n" + summary)

        # Generate PDF and send to the specified channel
        pdf_file = generate_pdf(user_id, user_info, lang)
        if pdf_file:
            await context.bot.send_document(chat_id="@Channel_ID", document=open(pdf_file, 'rb'), filename=pdf_file)
            os.remove(pdf_file)  # Clean up the generated file

        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text(t("invalid_number", lang))
        return CUST_AMOUNT  # Retry CUST_AMOUNT state

# Load the font that supports Latvian characters
pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))

def get_invoice_number() -> int:
    today = datetime.now().strftime("%d%m%y")
    folder = "./invoice_store"
    pattern = re.compile(fr"OG_{today}_(\d+)_.*\.pdf")
    numbers = []

    if not os.path.exists(folder):
        os.makedirs(folder)

    for filename in os.listdir(folder):
        match = pattern.match(filename)
        if match:
            numbers.append(int(match.group(1)))

    return max(numbers) + 1 if numbers else 1

def generate_pdf(user_id: str, user_info: dict, lang: str) -> str:
    # Generate a PDF invoice with tables
    today_str = datetime.now().strftime("%d%m%y")
    invoice_number = get_invoice_number()
    user_info = user_data[user_id][-1]
    pdf_filename = f"OG_{today_str}_{invoice_number}_{user_info['first_name']}_{user_info['last_name']}.pdf"
    pdf_path = os.path.join("./invoice_store", pdf_filename)
    # Create a PDF document
    pdf = SimpleDocTemplate(pdf_filename, pagesize=A4)
    elements = []

    # Create the PDF document
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    elements = []

    # Header - Invoice and Date Information
    styles = getSampleStyleSheet()
    header_data = [ 
    ["Payer Name"],
    [f"{user_info.get('first_name', 'First Name')} {user_info.get('last_name', 'Last Name')}"],
    ["", " ", " "],  
    ["", " ", " "], 
    ["Request", " ", f"Invoice Nr NA/{today_str}/{invoice_number}"],
    ['LTD "Name"', " ", f"no {datetime.now().strftime('%d.%m.%Y')}"],
    ["Reģ. Nr 123456789", " ", " "],
    ["Street 12-34, City, P CODE", " ", " "],
    ['Account Number Nr 12345678987654321', " ", " "],
    ['From "BANK" SWIFT (BIC) kods: XYZ12345', " ", " "]
]

    header_table = Table(header_data, colWidths=[6 * cm, 2 * cm, 7 * cm])
    header_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'DejaVuSans', 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(header_table)

    # Add some space before the table
    elements.append(Table([[" "]]))

    # Main Invoice Table
    event_date = datetime.now() + timedelta(days=14)
    unit_price = 10.00
    total_amount = user_info.get('cust_amount', 0) * unit_price
    table_data = [
        ["TITEL", "DATE", "AMOUNT", "PRICE", "TOTAL"],
        [f"Open games {event_date.strftime('%d.%m.%y')}", "kompl.", str(user_info.get('cust_amount', 0)), "10.00 EUR", f"{total_amount:.2f} EUR"]
    ]

    invoice_table = Table(table_data, colWidths=[7 * cm, 2 * cm, 2 * cm, 3 * cm, 3 * cm])
    invoice_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'DejaVuSans', 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
    ]))
    elements.append(invoice_table)

    # Total Amount
    total_data = [
        ["", "", "", "TOTAL SUM", f"{total_amount:.2f} EUR"],
        ["", "", "", f"(SUM IN TEXT)", ""]
    ]

    total_table = Table(total_data, colWidths=[7 * cm, 2 * cm, 2 * cm, 3 * cm, 3 * cm])
    total_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'DejaVuSans', 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('SPAN', (0, 1), (1, 1)),
        ('SPAN', (3, 0), (4, 0)),
    ]))
    elements.append(total_table)

    doc.build(elements)
    return pdf_path

async def retrieve(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    registrations = user_data.get(user_id, [])

    if not registrations:
        await update.message.reply_text(t("no_registrations", lang))
    else:
        response = t("retrieve", lang)
        for i, reg in enumerate(registrations):
            response += f"{i + 1}. {t('first_name', lang)}: {reg.get('first_name', 'Unknown')}, {t('last_name', lang)}: {reg.get('last_name', 'Unknown')}, {t('email', lang)}: {reg.get('email', 'Unknown')}, {t('number_of_people', lang)}: {reg.get('cust_amount', 'Unknown')}\n"
        await update.message.reply_text(response)

def main() -> None:
    app = Application.builder().token("YOUR_BOT_TOKEN").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANGUAGE: [CallbackQueryHandler(select_language)],
            FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_first_name)],
            LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_last_name)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
            CUST_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_cust_amount)],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('retrieve', retrieve))

    app.run_polling()

if __name__ == '__main__':
    main()
