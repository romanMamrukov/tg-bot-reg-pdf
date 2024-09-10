import pandas as pd
import json
import os
import logging
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Bot, Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext
from urllib.parse import urlparse, parse_qs
from pdf_invoice import generate_pdf

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# File paths
DATA_FILE = "user_data.json"
TRANSLATIONS_FILE = "translations.json"
BOT_CONFIG_FILE = "bot_config.json"
PDF_SETTINGS_FILE = "pdf_settings.json"
GAME_FILE = "games.csv"

# Bot tokens
ANNOUNCE_BOT_TOKEN = "ANNOUNCE_BOT_TOKEN"
REGISTRATION_BOT_TOKEN = "REGISTRATION_BOT_TOKEN"

# Channel names
ANNOUNCE_CHANNEL = "@ANNOUNCE_CHANNEL"
REGISTRATION_CHANNEL = "@REGISTRATION_CHANNEL"

# Define states for the conversation
LANGUAGE, MAIN_MENU, FIRST_NAME, LAST_NAME, EMAIL, CUST_AMOUNT = range(6)

# Load existing user data
def load_user_data(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except json.JSONDecodeError:
            return {}
    return {}

user_data = load_user_data(DATA_FILE)

# Load translations
def load_translations():
    with open(TRANSLATIONS_FILE, 'r', encoding='utf-8') as file:
        return json.load(file)

translations = load_translations()

# Load bot configuration
def load_bot_config():
    with open(BOT_CONFIG_FILE, 'r', encoding='utf-8') as file:
        return json.load(file)

bot_config = load_bot_config()

# Load PDF settings
def load_pdf_settings():
    with open(PDF_SETTINGS_FILE, 'r', encoding='utf-8') as file:
        return json.load(file)

pdf_settings = load_pdf_settings()

# Load game data
def load_games(file_path):
    try:
        logging.info("Loading game data...")
        games_df = pd.read_csv(file_path)
        games_df.columns = games_df.columns.str.strip()  # Clean column names
        games_df['price_per_person'] = pd.to_numeric(games_df['price_per_person'], errors='coerce').fillna(0).astype(int)
        games_df['spots_all'] = pd.to_numeric(games_df['spots_all'], errors='coerce').fillna(0).astype(int)
        games_df['spots_registered'] = pd.to_numeric(games_df['spots_registered'], errors='coerce').fillna(0).astype(int)
        games_df['spots_left'] = pd.to_numeric(games_df['spots_left'], errors='coerce').fillna(0).astype(int)
        return games_df.to_dict(orient='records')
    except Exception as e:
        logging.error(f"Error loading game data: {e}")
        return []

games = load_games(GAME_FILE)

# Helper functions
def escape_markdown(text):
    if not isinstance(text, str):
        text = str(text)
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + char if char in escape_chars else char for char in text])

def t(key: str, lang: str = 'en') -> str:
    return translations.get(lang, translations['en']).get(key, key)

def extract_game_info(update: Update):
    query = urlparse(update.message.text).query
    params = parse_qs(query)
    return {
        "game_id": params.get('game_id', [''])[0],
        "game_name": params.get('name', [''])[0],
        "game_place": params.get('place', [''])[0],
        "game_time": params.get('time', [''])[0],
        "game_price": params.get('price', [''])[0]
    }

# Announce games
async def send_game_announcements(games):
    logging.info("Checking for upcoming games...")
    today = datetime.now().date()
    end_date = today + timedelta(days=7)
    upcoming_games = [
        game for game in games
        if today <= datetime.strptime(game['date'], "%Y-%m-%d").date() <= end_date
    ]
    if not upcoming_games:
        logging.info("No upcoming games within the next 7 days.")
    for game in upcoming_games:
        try:
            logging.info(f"Announcing game: {game['game_name']}")
            await announce_game(game)
        except Exception as e:
            logging.error(f"Error sending announcement for game {game['game_name']}: {e}")

async def announce_game(game):
    try:
        registration_link = (
            f"https://t.me/{REGISTRATION_BOT_TOKEN}/register?game_id={game['game_id']}&name={game['game_name']}&place={game['place']}&date={game['date']}&time={game['time']}&price={game['price_per_person']}"
        )
        message = (
            f"📢 *Upcoming Game*\n\n"
            f"🏆 *{escape_markdown(game['game_name'])}*\n"
            f"📍 About: {escape_markdown(game['description'])}\n"
            f"📍 Place: {escape_markdown(game['place'])}\n"
            f"🗓️ Date: {escape_markdown(game['date'])}\n"
            f"🕒 Time: {escape_markdown(game['time'])}\n"
            f"🎟️ Spots Available: {escape_markdown(str(game['spots_all']))}\n"
            f"🎟️ Ticket Price: {escape_markdown(f'€{game['price_per_person']:.2f}')}\n"
            f"[Register here]({escape_markdown(registration_link)})"
        )
        await telegram_bot.send_message(chat_id=ANNOUNCE_CHANNEL, text=message, parse_mode='MarkdownV2')
        logging.info(f"Message sent for {game['game_name']}")
    except Exception as e:
        logging.error(f"Error sending message for {game['game_name']}: {e}")

async def auto_announce_games():
    if games:
        await send_game_announcements(games)

def schedule_repeated_announcements():
    scheduler = BackgroundScheduler()
    scheduler.add_job(auto_announce_games, 'interval', hours=8)
    scheduler.start()
    logging.info("Scheduler started: announcing games every 8 hours.")

# Immediate announcement on startup
async def announce_games_on_startup():
    if games:
        await send_game_announcements(games)

# Conversation handlers
async def start(update: Update, context: CallbackContext) -> int:
    game_info = extract_game_info(update)
    context.chat_data['game_info'] = game_info
    user_id = str(update.message.from_user.id)
    lang = user_data.get(user_id, [{}])[-1].get('lang', 'en')
    language_buttons = bot_config.get('language_buttons', ["English", "Latviešu", "Русский"])
    buttons = [KeyboardButton(btn) for btn in language_buttons]
    keyboard = [buttons]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(t("select_language", lang), reply_markup=reply_markup)
    return LANGUAGE

async def select_language(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang_selection = update.message.text.lower()
    if "latviešu" in lang_selection:
        lang = 'lv'
    elif "русский" in lang_selection:
        lang = 'ru'
    else:
        lang = 'en'
    user_data.setdefault(user_id, []).append({'lang': lang})
    return await main_menu(update, context)

async def main_menu(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    if 'game_info' not in context.chat_data:
        context.chat_data['game_info'] = {}
    game_info = context.chat_data['game_info']
    if game_info:
        await update.message.reply_text(
            f"{t('registering_for', lang)}\n"
            f"🕹️ {t('game_name', lang)}: {game_info.get('game_name')}\n"
            f"📍 {t('place', lang)}: {game_info.get('game_place')}\n"
            f"🕒 {t('time', lang)}: {game_info.get('game_time')}\n"
            f"💵 {t('price', lang)}: {game_info.get('game_price')}\n"
        )
    else:
        await update.message.reply_text(t('choose_action', lang))
    buttons = [
        KeyboardButton(t('register', lang)),
        KeyboardButton(t('cancel', lang))
    ]
    keyboard = [buttons]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(t('main_menu', lang), reply_markup=reply_markup)
    return MAIN_MENU

async def register(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    await update.message.reply_text(t('enter_first_name', lang))
    return FIRST_NAME

async def enter_first_name(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    context.user_data['first_name'] = update.message.text
    await update.message.reply_text(t('enter_last_name', lang))
    return LAST_NAME

async def enter_last_name(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    context.user_data['last_name'] = update.message.text
    await update.message.reply_text(t('enter_email', lang))
    return EMAIL

async def enter_email(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    context.user_data['email'] = update.message.text
    await update.message.reply_text(t('enter_amount', lang))
    return CUST_AMOUNT

async def enter_amount(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    amount = int(update.message.text)
    context.user_data['amount'] = amount
    game_info = context.chat_data['game_info']
    total_price = amount * float(game_info.get('game_price', 0))
    pdf_path = generate_pdf(context.user_data, total_price)
    await update.message.reply_text(f"{t('invoice_sent', lang)} {pdf_path}")
    await update.message.reply_document(open(pdf_path, 'rb'))
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    user_id = str(update.message.from_user.id)
    lang = user_data[user_id][-1]['lang']
    await update.message.reply_text(t('operation_cancelled', lang))
    return ConversationHandler.END

# Main function
async def main() -> None:
    global telegram_bot
    telegram_bot = Bot(token=ANNOUNCE_BOT_TOKEN)
    application = Application.builder().token(ANNOUNCE_BOT_TOKEN).build()

    # Immediate announcement on startup
    await announce_games_on_startup()

    scheduler = BackgroundScheduler()
    scheduler.add_job(auto_announce_games, 'interval', hours=8)
    scheduler.start()
    logging.info("Scheduler started: announcing games every 8 hours.")
    
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_language)],
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu)],
            FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_first_name)],
            LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_last_name)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_email)],
            CUST_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(conversation_handler)
    
    # Run the bot
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
