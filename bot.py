import json
import os
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# Define states for the conversation
LANGUAGE, MAIN_MENU, FIRST_NAME, LAST_NAME, EMAIL, CUST_AMOUNT = range(6)

# File path to store user data
DATA_FILE = "user_data.json"

# Load existing user data from file
def load_user_data(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except json.JSONDecodeError:
            return {}
    return {}

user_data = load_user_data(DATA_FILE)

# Language translation dictionary
translations = {
    "en": {
        "start": "Hello! I'm OpenGames bot. I can help you with registration and retrieve your previous registrations.",
        "select_language": "Please select your preferred language:",
        "register": "Register",
        "retrieve": "Retrieve Data",
        "change_language": "Change Language",
        "ask_first_name": "Let's start with your registration. What's your first name?",
        "ask_last_name": "Great! Now, what's your surname?",
        "ask_email": "Perfect! Can you provide your email address?",
        "ask_cust_amount": "Thanks! How many people will be attending?",
        "thank_you": "Thank you for the information! Here's a summary of your registration:",
        "invalid_number": "Please enter a valid number for the number of people.",
        "no_registrations": "You have no previous registrations.",
        "first_name": "First Name",
        "last_name": "Last Name",
        "email": "Email",
        "number_of_people": "Number of People",
        "new_registration": "New Registration",
        "pdf_invoice": "Invoice PDF",
        "main_menu": "What would you like to do next?",
    },
    "lv": {
        "start": "Sveiki! Es esmu OpenGames bots. Es varu jums palīdzēt ar reģistrāciju un atgūt jūsu iepriekšējās reģistrācijas.",
        "select_language": "Lūdzu, izvēlieties vēlamo valodu:",
        "register": "Reģistrēties",
        "retrieve": "Apskatīt datus",
        "change_language": "Mainīt valodu",
        "ask_first_name": "Sāksim ar jūsu reģistrāciju. Kāds ir jūsu vārds?",
        "ask_last_name": "Lieliski! Kāds ir jūsu uzvārds?",
        "ask_email": "Perfekti! Vai varat norādīt savu e-pasta adresi?",
        "ask_cust_amount": "Paldies! Cik cilvēki piedalīsies?",
        "thank_you": "Paldies par informāciju! Šeit ir jūsu reģistrācijas kopsavilkums:",
        "invalid_number": "Lūdzu, ievadiet derīgu cilvēku skaitu.",
        "no_registrations": "Jums nav iepriekšēju reģistrāciju.",
        "first_name": "Vārds",
        "last_name": "Uzvārds",
        "email": "E-pasts",
        "number_of_people": "Cilvēku skaits",
        "new_registration": "Jauna reģistrācija",
        "pdf_invoice": "Rēķins PDF formātā",
        "main_menu": "Ko jūs vēlētos darīt tālāk?",
    },
    "ru": {
        "start": "Привет! Я бот OpenGames. Я могу помочь вам с регистрацией и получить ваши предыдущие регистрации.",
        "select_language": "Пожалуйста, выберите предпочитаемый язык:",
        "register": "Регистрация",
        "retrieve": "Получить данные",
        "change_language": "Изменить язык",
        "ask_first_name": "Начнем с вашей регистрации. Как ваше имя?",
        "ask_last_name": "Отлично! Как ваша фамилия?",
        "ask_email": "Прекрасно! Можете указать свой адрес электронной почты?",
        "ask_cust_amount": "Спасибо! Сколько человек будет присутствовать?",
        "thank_you": "Спасибо за информацию! Вот сводка вашей регистрации:",
        "invalid_number": "Пожалуйста, введите действительное количество человек.",
        "no_registrations": "У вас нет предыдущих регистраций.",
        "first_name": "Имя",
        "last_name": "Фамилия",
        "email": "Электронная почта",
        "number_of_people": "Количество человек",
        "new_registration": "Новая регистрация",
        "pdf_invoice": "PDF-счет",
        "main_menu": "Что бы вы хотели сделать дальше?",
    }
}

# Function to retrieve the translation
def t(key: str, lang: str = 'en') -> str:
    return translations.get(lang, translations['en']).get(key, key)

async def start(update: Update, context: CallbackContext) -> int:
    # Display welcome message in all languages
    welcome_message = (
        f"{translations['en']['start']}\n\n"
        f"{translations['lv']['start']}\n\n"
        f"{translations['ru']['start']}\n\n"
    )
    await update.message.reply_text(welcome_message)

    # Offer language selection with buttons
    keyboard = [
        [KeyboardButton("English"), KeyboardButton("Latviešu"), KeyboardButton("Русский")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(t("select_language", 'en'), reply_markup=reply_markup)

    return LANGUAGE  # Transition to LANGUAGE state

async def select_language(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang_selection = update.message.text.lower()

    # Determine the selected language
    if "latviešu" in lang_selection:
        lang = 'lv'
    elif "русский" in lang_selection:
        lang = 'ru'
    else:
        lang = 'en'

    # Store user's language choice
    user_data.setdefault(user_id, []).append({'lang': lang})

    return await main_menu(update, context)

async def main_menu(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']

    # Offer main menu options with buttons
    keyboard = [
        [KeyboardButton(t("register", lang)), KeyboardButton(t("retrieve", lang))],
        [KeyboardButton(t("change_language", lang))]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(t("main_menu", lang), reply_markup=reply_markup)

    return MAIN_MENU  # Transition to MAIN_MENU state

async def handle_main_menu(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    selection = update.message.text

    if selection == t("register", lang):
        await update.message.reply_text(t("ask_first_name", lang))
        return FIRST_NAME  # Transition to FIRST_NAME state

    elif selection == t("retrieve", lang):
        await retrieve(update, context)
        return MAIN_MENU  # Stay in MAIN_MENU state

    elif selection == t("change_language", lang):
        return await start(update, context)  # Go back to start to change language

async def ask_first_name(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    first_name = update.message.text

    # Store the user's first name
    user_data[user_id][-1]['first_name'] = first_name

    await update.message.reply_text(t("ask_last_name", lang))
    return LAST_NAME  # Transition to LAST_NAME state

async def ask_last_name(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    last_name = update.message.text

    # Store the user's surname
    user_data[user_id][-1]['last_name'] = last_name

    await update.message.reply_text(t("ask_email", lang))
    return EMAIL  # Transition to EMAIL state

async def ask_email(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    email = update.message.text

    # Store the user's email address
    user_data[user_id][-1]['email'] = email

    await update.message.reply_text(t("ask_cust_amount", lang))
    return CUST_AMOUNT  # Transition to CUST_AMOUNT state

async def ask_cust_amount(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    cust_amount = update.message.text

    try:
        cust_amount = int(cust_amount)
        user_data[user_id][-1]['cust_amount'] = cust_amount
    except ValueError:
        await update.message.reply_text(t("invalid_number", lang))
        return CUST_AMOUNT  # Stay in CUST_AMOUNT state

    # Generate PDF summary
    pdf_file = generate_pdf(user_id, user_data[user_id][-1], lang)
        if pdf_file:
        await context.bot.send_document(chat_id="@chanel_name", document=open(pdf_file, 'rb'), filename=pdf_file)
        os.remove(pdf_file)  # Clean up the generated file

    # Send summary and PDF
    summary = (
        f"{t('first_name', lang)}: {user_data[user_id][-1]['first_name']}\n"
        f"{t('last_name', lang)}: {user_data[user_id][-1]['last_name']}\n"
        f"{t('email', lang)}: {user_data[user_id][-1]['email']}\n"
        f"{t('number_of_people', lang)}: {cust_amount}\n"
    )
    await update.message.reply_text(f"{t('thank_you', lang)}\n\n{summary}")
    await update.message.reply_document(document=open(pdf_file, 'rb'))

    # Send the summary to the specified channel
    await context.bot.send_message(chat_id="@og_cc_pdf", text=f"{t('new_registration', lang)}:\n\n" + summary)

    return await main_menu(update, context)  # Go back to main menu after registration

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
    ["Maksātājs"],
    [f"{user_info.get('first_name', 'First Name')} {user_info.get('last_name', 'Last Name')}"],
    ["", " ", " "],  
    ["", " ", " "], 
    ["Piegādātājs", " ", f"RĒĶINS Nr OG/{today_str}/{invoice_number}"],
    ['LTD "Company"', " ", f"no {datetime.now().strftime('%d.%m.%Y')}"],
    ["Reģ. Nr 123456789", " ", " "],
    ["Street 12-34, City, Post-Code", " ", " "],
    ['Norēķinu konta Nr ', " ", " "],
    ['AS "Banka" SWIFT (BIC) kods: 123456', " ", " "]
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
        ["Nosaukums", "Mērv.", "Daudzums", "Cena", "Summa"],
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
        ["", "", "Kopā apmaksai", f"{total_amount:.2f} EUR"],
        ["", "", "", f"(Euro un centi)"]
    ]

    total_table = Table(total_data, colWidths=[7 * cm, 2 * cm, 2 * cm, 6 * cm])
    total_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'DejaVuSans', 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('SPAN', (0, 1), (2, 1)),  # Span the first three columns in the second row
    ]))
    elements.append(total_table)

    doc.build(elements)
    return pdf_path


async def retrieve(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.from_user.id)
    if user_id in user_data and user_data[user_id]:
        registrations = user_data[user_id]
        for i, reg in enumerate(registrations, start=1):
            lang = reg.get('lang', 'en')
            summary = (
                f"{i}. {t('first_name', lang)}: {reg.get('first_name', 'Unknown')}, "
                f"{t('last_name', lang)}: {reg.get('last_name', 'Unknown')}, "
                f"{t('email', lang)}: {reg.get('email', 'Unknown')}, "
                f"{t('number_of_people', lang)}: {reg.get('cust_amount', 'Unknown')}\n"
            )
            await update.message.reply_text(summary)
    else:
        await update.message.reply_text(t("no_registrations", 'en'))

def main():
    token = "YOUR_BOT_TOKEN"
    app = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_language)],
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)],
            FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_first_name)],
            LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_last_name)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)],
            CUST_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_cust_amount)],
        },
        fallbacks=[],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("retrieve", retrieve))

    app.run_polling()

if __name__ == "__main__":
    main()
