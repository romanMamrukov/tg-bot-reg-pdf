import json
import os
from datetime import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext

# Import the PDF generation functions
from pdf_invoice import generate_pdf

# Define states for the conversation
LANGUAGE, MAIN_MENU, FIRST_NAME, LAST_NAME, EMAIL, CUST_AMOUNT = range(6)

# File path to store user data
DATA_FILE = "user_data.json"
# File path to store translation data
TRANSLATIONS_FILE = "translations.json"
# FORWARD Channel name
channel = "@YOUR_CHANNEL_NAME"
# BOT TOKEN 
token = "YOUR_BOT_TOKEN"

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

# Load translations from the JSON file
if os.path.exists(TRANSLATIONS_FILE):
    with open(TRANSLATIONS_FILE, 'r', encoding='utf-8') as file:
        translations = json.load(file)
else:
    raise FileNotFoundError(f"{TRANSLATIONS_FILE} not found!")

# Function to retrieve the translation
def t(key: str, lang: str = 'en') -> str:
    return translations.get(lang, translations['en']).get(key, key)

async def start(update: Update, context: CallbackContext) -> int:
    # Display welcome message in all languages
    combined_message = "\n\n".join([t("start", lang_code) for lang_code in translations])
    await update.message.reply_text(combined_message)

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
        return await start(update, context)  # Restart the language selection

    else:
        await update.message.reply_text(t("invalid_option", lang))
        return MAIN_MENU  # Stay in MAIN_MENU state

async def get_first_name(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    first_name = update.message.text

    # Store user's first name
    user_data[user_id][-1]['first_name'] = first_name

    await update.message.reply_text(t("ask_last_name", lang))
    return LAST_NAME  # Transition to LAST_NAME state

async def get_last_name(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    last_name = update.message.text

    # Store user's last name
    user_data[user_id][-1]['last_name'] = last_name

    await update.message.reply_text(t("ask_email", lang))
    return EMAIL  # Transition to EMAIL state

async def get_email(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    email = update.message.text

    # Store user's email
    user_data[user_id][-1]['email'] = email

    await update.message.reply_text(t("ask_cust_amount", lang))
    return CUST_AMOUNT  # Transition to CUST_AMOUNT state

async def get_cust_amount(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    cust_amount = int(update.message.text)

    # Store user's customer amount
    try:
        cust_amount = int(cust_amount)
        user_data[user_id][-1]['cust_amount'] = cust_amount
    except ValueError:
        await update.message.reply_text(t("invalid_number", lang))
        return CUST_AMOUNT  # Stay in CUST_AMOUNT state

    # Send summary and PDF
    summary = (
        f"{t('first_name', lang)}: {user_data[user_id][-1]['first_name']}\n"
        f"{t('last_name', lang)}: {user_data[user_id][-1]['last_name']}\n"
        f"{t('email', lang)}: {user_data[user_id][-1]['email']}\n"
        f"{t('number_of_people', lang)}: {cust_amount}\n"
    )
    await update.message.reply_text(f"{t('thank_you', lang)}\n\n{summary}")

    # Send the summary to the specified channel
    await context.bot.send_message(chat_id=channel, text=f"{t('new_registration', lang)}:\n\n" + summary)

    # Generate the invoice PDF
    user_info = {key: value for d in user_data[user_id] for key, value in d.items()}
    pdf_path = generate_pdf(user_id, user_info, lang)

    # Generate PDF summary
    await context.bot.send_document(chat_id="@og_cc_pdf", document=open(pdf_path, 'rb'), filename=pdf_path)
    await update.message.reply_document(open(pdf_path, "rb"))

    # Go back to the main menu
    return await main_menu(update, context)

async def retrieve(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']

    # Check if user data exists
    if user_id not in user_data:
        await update.message.reply_text(t("no_data", lang))
    else:
        # Retrieve user data
        user_info = {key: value for d in user_data[user_id] for key, value in d.items()}
        await update.message.reply_text(t("retrieve_data", lang).format(
            first_name=user_info['first_name'],
            last_name=user_info['last_name'],
            email=user_info['email'],
            cust_amount=user_info['cust_amount']
        ))

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Conversation cancelled.")
    return ConversationHandler.END

def main() -> None:
    # Create the application and pass it your bot's token.
    app = Application.builder().token(token).build()

    # Set up the conversation handler with the states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_language)],
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)],
            FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_first_name)],
            LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_last_name)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            CUST_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_cust_amount)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add the conversation handler to the application
    app.add_handler(conv_handler)

    # Run the bot until you press Ctrl-C
    app.run_polling()

if __name__ == "__main__":
    main()
