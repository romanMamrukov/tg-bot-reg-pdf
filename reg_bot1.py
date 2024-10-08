import csv
import json
import os
import base64
import httpx
import logging
import asyncio
import yagmail
import httpx
import stripe
import threading
import pandas as pd
from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from urllib.parse import parse_qs, urlparse
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext
from common.pdf_invoice import generate_pdf, user_invoice_num
from common.file_manager import get_game_info, update_game_csv, store_user_data, get_user_data, cancel_registration_fun, save_json
from common.validation import is_valid_email, is_valid_attendee_count, is_valid_deeplink, is_valid_invoice
from dotenv import load_dotenv
from datetime import datetime, timedelta
from common.reg_handler import RegistrationHandler
from common.stripe_handler import StripeHandler

"""This bot works with 
Registration, 
Language selection, 
Posts summary of the game before registraion,
Posts summary of the game and registation after registration, 
PDF invoice generator post it to user,
PDF invoice generated and posted to other group channel along with registartion summary, 
Stores and retreive registration data,
Update games.csv data with users registred to keep available spots updated,
Store user invoice number,
Cancle registration - mark in user data,
Payment link
Invoice and registration summary over email to user and admin
"""
""" TODO 
Confirm payment - Only in STRIPE dashboard manually
Reminder of the paymnet
Reminder of the upcoming game to user
Optimise performance and refactor code
"""

# Define states for the conversation
LANGUAGE, MAIN_MENU, FULL_NAME, EMAIL, CUST_AMOUNT, CANCEL_INVOICE = range(6)

# File paths
DATA_FILE = "./store/user_data.json" #Store and retreave user_data
TRANSLATIONS_FILE = "./store/translations.json" #Translation Dictionary
BOT_CONFIG_FILE = "./common/bot_config.json"
PDF_SETTINGS_FILE = "./store/pdf_settings.json" #TODO adjustments to PDF not via code
GAMES_CSV_FILE = "./store/games.csv" #Games info storage
DATABASE = "./common/tg_bot_db.db"

# LOAD TOKEN & CRED DETAILS
load_dotenv()

EMAIL_HOST = os.getenv("EMAIL_HOST") 
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD") 
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
CHANNEL_ID = os.getenv("CHANNEL_ID")
BOT_TOKEN = os.getenv("BOT_TOKEN")
# STRIP Credentials
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")  # Use your test secret key

# Function to connect to the SQLite database
def db_connect():
    conn = sqlite3.connect(DATABASE)
    return conn

# Load configurations and data
def load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError:
            return {}
    return {}

# Function to load user data
def load_user_data():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_csv(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, newline='', encoding='utf-8') as file:
                return list(csv.DictReader(file))
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return []
    return []

user_data = load_json(DATA_FILE)
translations = load_json(TRANSLATIONS_FILE)
bot_config = load_json(BOT_CONFIG_FILE)
pdf_settings = load_json(PDF_SETTINGS_FILE)
games = load_csv(GAMES_CSV_FILE)

# Function to get game information from CSV file
def get_game_info(game_id: str):
    try:
        with open(GAMES_CSV_FILE, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['game_id'] == game_id:
                    return row
    except FileNotFoundError:
        print("The file 'games.csv' was not found.")
    except Exception as e:
        print(f"An error occurred while reading the CSV file: {e}")
    return None

# Function to retrieve the translation
def t(key: str, lang: str = 'en') -> str:
    return translations.get(lang, translations['en']).get(key, key)

# Helper function to escape MarkdownV2 characters
def escape_markdown(text):
    if text is None:
        return ''
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    return ''.join(['\\' + char if char in escape_chars else char for char in text])

# Helper function to decode and parse deeplink
def decode_deeplink(encoded_start_data):
    try:
        encoded_start_data += '=' * (-len(encoded_start_data) % 4)
        decoded_start_data = base64.urlsafe_b64decode(encoded_start_data).decode('utf-8')
        params = parse_qs(decoded_start_data)
        if 'game_id' in params and isinstance(params['game_id'], list):
            params['game_id'] = params['game_id'][0]
        return params
    except Exception as e:
        print(f"Error decoding start data: {e}")
        return {}

async def start(update: Update, context: CallbackContext) -> int:
    try:
        if context.args:
            encoded_start_data = context.args[0]
            params = decode_deeplink(encoded_start_data)

            game_id = params.get('game_id', '')
            if game_id:
                game_info = get_game_info(game_id)
                
                if game_info:
                    context.chat_data['game_info'] = game_info
                    user_id = str(update.message.from_user.id)
                    lang = user_data.get(user_id, [{}])[-1].get('lang', 'en')

                    welcome_message = (
                        f"{t('start', 'en')}\n\n"
                        f"{t('start', 'lv')}\n\n"
                        f"{t('start', 'ru')}\n\n"
                    )

                    select_langauge_all = (
                        f"{t('select_language', 'en')}\n\n"
                        f"{t('select_language', 'lv')}\n\n"
                        f"{t('select_language', 'ru')}\n\n"
                    )
                    
                    await update.message.reply_text(welcome_message)

                    language_buttons = bot_config.get('language_buttons', ["English", "Latviešu", "Русский"])
                    buttons = [KeyboardButton(btn) for btn in language_buttons]
                    keyboard = [buttons]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
                    await update.message.reply_text(select_langauge_all, reply_markup=reply_markup)
                    
                    return LANGUAGE
                else:
                    await update.message.reply_text("Game not found.")
            else:
                await update.message.reply_text("Invalid or missing game_id.")
        else:
            await update.message.reply_text("No game information provided.")
    except Exception as e:
        await update.message.reply_text(f"An unexpected error occurred: {e}")

def get_language_code(lang_selection):
    if "latviešu" in lang_selection:
        return 'lv'
    elif "русский" in lang_selection:
        return 'ru'
    else:
        return 'en'

async def select_language(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang_selection = update.message.text.lower()

    lang = get_language_code(lang_selection)
    user_data.setdefault(user_id, []).append({'lang': lang})

    return await main_menu(update, context)

async def main_menu(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']

    game_info = context.chat_data.get('game_info', {})

    if game_info:
        game_name = escape_markdown(game_info.get('game_name', ''))
        game_place = escape_markdown(game_info.get('place', ''))
        game_date = escape_markdown(game_info.get('date', ''))
        game_time = escape_markdown(game_info.get('time', ''))
        game_price = escape_markdown(game_info.get('price_per_person', ''))

        await update.message.reply_text(
            f"📢 {t('registering_for', lang)}\n"
            f"🏆 {t('game', lang)}: {game_name}\n"
            f"📍 {t('place', lang)}: {game_place}\n"
            f"🕒 {t('date', lang)}: {game_date}\n"
            f"🕒 {t('time', lang)}: {game_time}\n"
            f"🎟️ {t('price_per_person', lang)}: €{game_price}\n"
        )
    else:
        await update.message.reply_text("Game information is missing.")

    keyboard = [
        [KeyboardButton(t("register", lang)), KeyboardButton(t("retrieve", lang))],
        [KeyboardButton(t("change_language", lang))], [KeyboardButton(t("cancel_registration", lang))]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(t("main_menu", lang), reply_markup=reply_markup)

    return MAIN_MENU

async def handle_main_menu(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    selection = update.message.text

    if selection == t("register", lang):
        await update.message.reply_text(t("ask_full_name", lang))
        return FULL_NAME

    elif selection == t("retrieve", lang):
        await retrieve(update, context)
        return MAIN_MENU

    elif selection == t("change_language", lang):
        select_langauge_all = (
                        f"{t('select_language', 'en')}\n\n"
                        f"{t('select_language', 'lv')}\n\n"
                        f"{t('select_language', 'ru')}\n\n"
                    )
        language_buttons = bot_config.get('language_buttons', ["English", "Latviešu", "Русский"])
        buttons = [KeyboardButton(btn) for btn in language_buttons]
        keyboard = [buttons]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(select_langauge_all, reply_markup=reply_markup)
        return LANGUAGE
    
    elif selection == t("cancel_registration", lang):
        await update.message.reply_text(t("provide_invoice", lang))
        return CANCEL_INVOICE

    else:
        await update.message.reply_text(t("invalid_option", lang))
        return MAIN_MENU

async def get_full_name(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    full_name = update.message.text

    # Store user's full name
    user_data[user_id][-1]['full_name'] = full_name

    await update.message.reply_text(t("ask_email", lang))
    return EMAIL

async def get_email(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    email = update.message.text

    # Validate the email
    if not is_valid_email(email):  # Assuming validate_email is your validation function
        await update.message.reply_text(t("invalid_email", lang))
        return EMAIL

    # Store user's email
    user_data[user_id][-1]['email'] = email

    await update.message.reply_text(t("ask_cust_amount", lang))
    return CUST_AMOUNT

async def get_cust_amount(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    cust_amount = update.message.text

    try:
        cust_amount = int(cust_amount)
        game_info = context.chat_data.get('game_info', {})
        spots_left = int(game_info.get('spots_left', 0))
        
        if not is_valid_attendee_count(cust_amount, spots_left):  # Assuming validate_cust_amount is your validation function
            await update.message.reply_text(t("invalid_number", lang))
            return CUST_AMOUNT

        if not game_info:
            await update.message.reply_text(t("game_info_missing", lang))
            return await MAIN_MENU

         # Check if there are enough spots available
        if cust_amount > spots_left:
            await update.message.reply_text(t("not_enough_spots", lang))
            return CUST_AMOUNT

        # Calculate total price
        price_per_person = float(game_info.get('price_per_person', 0))
        total_price = price_per_person * cust_amount
        print(f"Total price: {total_price}")

        user_data[user_id][-1]['cust_amount'] = cust_amount
        user_data[user_id][-1]['total_price'] = total_price

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': game_info.get('game_name', ''),
                        # Optionally add additional product details here
                    },
                    'unit_amount': int(round(total_price * 100)),  # Convert to cents
                },
                'quantity': 1,  # Assuming one item for the purchase
            }],
            mode='payment',
            metadata={'user_id': user_id},
            success_url='https://romanmamrukov.github.io/tg-bot-reg-pdf?status=success&session_id={CHECKOUT_SESSION_ID}&user_id={USER_ID}',
            cancel_url='https://romanmamrukov.github.io/tg-bot-reg-pdf?status=failed&session_id={CHECKOUT_SESSION_ID}&user_id={USER_ID}',
        )

        # Store the session URL and session ID in user data
        user_data[user_id][-1]['payment_link'] = session.url  # Use session.url for the payment link
        user_data[user_id][-1]['session_id'] = session.id  # Store the Stripe session ID

        # Generate the registration summary
        summary = (
            f"📢 {t('summary', lang)}\n"
            f"🏆 {t('game', lang)}: {escape_markdown(game_info.get('game_name', ''))}\n"
            f"📍 {t('place', lang)}: {escape_markdown(game_info.get('place', ''))}\n"
            f"🕒 {t('date', lang)}: {escape_markdown(game_info.get('date', ''))}\n"
            f"🕒 {t('time', lang)}: {escape_markdown(game_info.get('time', ''))}\n"
            f"🎟️ {t('price_per_person', lang)}: €{escape_markdown(game_info.get('price_per_person', ''))}\n"
            f"👤 {t('full_name', lang)}: {escape_markdown(user_data[user_id][-1]['full_name'])}\n"
            f"✉️ {t('email', lang)}: {escape_markdown(user_data[user_id][-1]['email'])}\n"
            f"🧑‍🤝‍🧑 {t('attendees', lang)}: {cust_amount}\n"
            f"💶 {t('total_price', lang)}: €{total_price:.2f}\n"
        )

        # Send payment link with summary and PDF
        await update.message.reply_text(
            f"Your registration summary:\n\n{summary}\n\n"
            f"Click this link to pay: {session.url}"
        )

        user_data[user_id][-1]['game_details'] = {
                'game_name': game_info.get('game_name', ''),
                'place': game_info.get('place', ''),
                'date': game_info.get('date', ''),
                'time': game_info.get('time', ''),
                'price_per_person': game_info.get('price_per_person', '')
            }
        
        # Generate PDF invoice
        pdf_file_path = generate_pdf(user_data[user_id][-1], game_info, lang)
        user_invoice = user_invoice_num()
        user_data[user_id][-1]['invoice_number'] = user_invoice

        if not os.path.exists(pdf_file_path):
            await update.message.reply_text("Error: PDF file not found.")
        else:
            user_data[user_id][-1]['pdf_path'] = pdf_file_path
        
        if os.path.exists(pdf_file_path) and os.path.getsize(pdf_file_path) > 0:
            try:
                # Send PDF to the user
                with open(pdf_file_path, 'rb') as pdf_file:
                    await update.message.reply_document(pdf_file)
                
                # Send PDF to the channel
                with open(pdf_file_path, 'rb') as pdf_file:
                    await context.bot.send_message(chat_id=CHANNEL_ID, text=f"{t('new_registration', lang)}:\n\n" + summary)
                    await context.bot.send_document(chat_id=CHANNEL_ID, document=pdf_file)

            except Exception as e:
                logging.error(f"Error sending PDF: {e}")
                await update.message.reply_text(f"Error occurred while sending PDF: {e}")

        # Update game CSV with new spots
        update_game_csv(game_info['game_id'], spots_registered=int(game_info.get('spots_registered', 0)) + cust_amount)

        # Save user data to user_data.json
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=4)

        # Send registration summary email
        send_registration_email(user_data[user_id][-1], lang)

        
        await update.message.reply_text(t("registration_complete", lang))
        keyboard = [
            [KeyboardButton(t("register", lang)), KeyboardButton(t("retrieve", lang))],
            [KeyboardButton(t("change_language", lang))], [KeyboardButton(t("cancel_registration", lang))]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

        await update.message.reply_text(t("main_menu", lang), reply_markup=reply_markup)
        return MAIN_MENU

    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text(t("invalid_number", lang))
        return CUST_AMOUNT

def send_registration_email(user_data: dict, lang: str):
    """Sends a registration summary email to the user and the admin."""
    try:
        yag = yagmail.SMTP(EMAIL_USER, EMAIL_PASSWORD, host=EMAIL_HOST)
        game_details = user_data.get('game_details', {})

        user_summary = (
            f"📢 {t('summary', lang)}\n"
            f"👤 {t('full_name', lang)}: {escape_markdown(user_data[user_id][-1]['full_name'])}\n"
            f"✉️ {t('email', lang)}: {reg.get('email', '')}\n"
            f"🧑‍🤝‍🧑 {t('attendees', lang)}: {reg.get('cust_amount', 1)}\n"
            f"💶 {t('total_price', lang)}: €{reg.get('total_price', 0):.2f}\n"
            f"🏆 {t('game', lang)}: {game_details.get('game_name', '')}\n"
            f"📍 {t('place', lang)}: {game_details.get('place', '')}\n"
            f"🕒 {t('date', lang)}: {game_details.get('date', '')}\n"
            f"🕒 {t('time', lang)}: {game_details.get('time', '')}\n"
            f"📄 {t('invoice_number', lang)}: {user_data.get('invoice_number', '')}\n"
        )

        # Send email to user
        yag.send(
            to=user_data.get('email', ''),
            subject=f"{t('registration_confirmation', lang)}",
            contents=user_summary,
            attachments=[user_data.get('pdf_path')] 
        )

        # Send email to admin
        yag.send(
            to=ADMIN_EMAIL,
            subject=f"{t('new_registration', lang)}",
            contents=user_summary,
            attachments=[user_data.get('pdf_path')] 
        )

        print("Registration confirmation emails sent successfully.")

    except Exception as e:
        print(f"Error sending email: {e}")

# Function to process payment updates
async def check_payment_updates():
    while True:
        user_data = load_json(DATA_FILE)
        
        # Iterate over users and check for payment updates
        for user_id, registrations in user_data.items():
            for registration in registrations:
                if registration.get('payment_status') == 'complete' and not registration.get('notified'):
                    # Send success message
                    await send_success_message(user_id)
                    registration['notified'] = True  # Mark as notified

                elif registration.get('payment_status') == 'canceled' and not registration.get('notified'):
                    # Send cancel message
                    await send_cancel_message(user_id)
                    registration['notified'] = True  # Mark as notified

        # Save the updated user_data with notification status
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=4)

        # Wait some time before checking again (e.g., every 10 seconds)
        await asyncio.sleep(10)

async def send_success_message(user_id):
    """Send a success message to the user via Telegram."""
    await telegram_app.bot.send_message(chat_id=user_id, text="Your payment was successful!")

async def send_cancel_message(user_id):
    """Send a cancel message to the user via Telegram."""
    await telegram_app.bot.send_message(chat_id=user_id, text="Your payment was canceled.")

def update_game_csv(game_id: str, spots_registered: int):
    df = pd.read_csv(GAMES_CSV_FILE)
    # Update the number of spots registered
    df.loc[df['game_id'] == game_id, 'spots_registered'] = spots_registered
    # Calculate and update the number of spots left
    df.loc[df['game_id'] == game_id, 'spots_left'] = df['spots_all'] - df['spots_registered']
    df.to_csv(GAMES_CSV_FILE, index=False)

async def retrieve(update: Update, context: CallbackContext) -> None:
    """Retrieve previous registrations."""
    user_data = load_json(DATA_FILE)
    user_id = str(update.message.from_user.id)
    lang = user_data.get(user_id, [{}])[-1].get('lang', 'en')

    if user_id not in user_data or not user_data[user_id]:
        await update.message.reply_text(t("no_registrations", lang))
    else:
        previous_registrations = user_data[user_id]
        for reg in previous_registrations:
            reg_summary = (
                f"👤 {t('full_name', lang)}: {escape_markdown(user_data[user_id][-1]['full_name'])}\n"
                f"✉️ {t('email', lang)}: {reg.get('email', '')}\n"
                f"🧑‍🤝‍🧑 {t('attendees', lang)}: {reg.get('cust_amount', 1)}\n"
                f"💶 {t('total_price', lang)}: €{reg.get('total_price', 0):.2f}\n"
                f"🏆 {t('game', lang)}: {reg.get('game_details', {}).get('game_name', '')}\n"
                f"📍 {t('place', lang)}: {reg.get('game_details', {}).get('place', '')}\n"
                f"🕒 {t('date', lang)}: {reg.get('game_details', {}).get('date', '')}\n"
                f"🕒 {t('time', lang)}: {reg.get('game_details', {}).get('time', '')}\n"
                f"📄 {t('invoice_number', lang)}: {reg.get('invoice_number', '')}\n"
            )
            
            # Only include the "Canceled" line if the registration is canceled
            if reg.get('canceled'):
                reg_summary += f"⚠️ {t('canceled', lang)}: {t('canceled', lang)}\n"
            await update.message.reply_text(reg_summary)

            # Send PDF if available
            pdf_path = reg.get('pdf_path')
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as pdf_file:
                    await update.message.reply_document(pdf_file)
            else:
                await update.message.reply_text(t("pdf_not_found", lang))

    keyboard = [
        [KeyboardButton(t("register", lang)), KeyboardButton(t("retrieve", lang))],
        [KeyboardButton(t("change_language", lang))], [KeyboardButton(t("cancel_registration", lang))]
        ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(t("main_menu", lang), reply_markup=reply_markup)
    return MAIN_MENU

async def cancel_registration(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data.get(user_id, [{}])[-1].get('lang', 'en')

    invoice_number = update.message.text

    if is_valid_invoice(user_data, invoice_number):
        if cancel_registration_fun(user_id, invoice_number):
            await update.message.reply_text(t("cancellation_successful", lang))
        else:
            await update.message.reply_text(t("cancellation_failed", lang))
    else:
        await update.message.reply_text(t("invalid_invoice", lang))

    keyboard = [
        [KeyboardButton(t("register", lang)), KeyboardButton(t("retrieve", lang))],
        [KeyboardButton(t("change_language", lang))], [KeyboardButton(t("cancel_registration", lang))]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(t("main_menu", lang), reply_markup=reply_markup)
    return MAIN_MENU

# Set up the bot
def main():
    # Set up logging
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Create the application
    app_bot = Application.builder().token(BOT_TOKEN).build()

    # Define the conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_language)],
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)],
            FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_full_name)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            CUST_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_cust_amount)],
            CANCEL_INVOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, cancel_registration)],
        },
        fallbacks=[CommandHandler("start", start), MessageHandler(filters.COMMAND, start)],
    )

    # Add the conversation handler to the application
    app_bot.add_handler(conv_handler)
    
    # Run the bot
    app_bot.run_polling()

if __name__ == "__main__":
    main()
