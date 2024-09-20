import logging
import asyncio
import base64
import os
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from telegram.ext import Application
from urllib.parse import quote_plus
from common.file_manager import load_csv  # Load CSV file from file_manager

# Your Telegram bot token and Channel
telegram_bot_token = "7397195211:AAESSWLWMTg9wNhsbx_ugEP4ygkfu8X1O_k"
channel_id = "@og_announ"  # Replace with your Telegram channel name

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Telegram Bot
telegram_bot = Bot(token=telegram_bot_token)

# Global variable to store games data
games = []
last_message_id = None

def load_games():
    """Load game data from the games.csv file."""
    file_path = os.path.abspath("./store/games.csv")
    if os.path.exists(file_path):
        global games
        games = load_csv(file_path)
        logging.info(f"Loaded {len(games)} games from games.csv")
    else:
        logging.error(f"File not found: {file_path}")

def generate_registration_link(game_id):
    """Generate a deeplink for game registration."""
    query = f"game_id={quote_plus(game_id)}"
    encoded_query = base64.urlsafe_b64encode(query.encode()).decode()
    return f"https://t.me/opengames_cc_pdf_bot?start={encoded_query}"

def escape_markdown(text):
    """Escape MarkdownV2 special characters."""
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + char if char in escape_chars else char for char in text])

async def send_game_announcements():
    """Send a combined announcement for all games within the next 7 days and pin the message."""
    today = datetime.now().date()
    end_date = today + timedelta(days=7)

    # Filter upcoming games that are not fully booked
    upcoming_games = [game for game in games if today <= datetime.strptime(game['date'], "%Y-%m-%d").date() <= end_date and int(game['spots_left']) > 0]

    if not upcoming_games:
        logging.info("No upcoming games to announce.")
        return

    message = "📢 *Upcoming Games*\n\n"
    for game in upcoming_games:
        message += (
            f"🏆 *{escape_markdown(game['game_name'])}*\n"
            f"📍 About: {escape_markdown(game['description'])}\n"
            f"📍 Place: {escape_markdown(game['place'])}\n"
            f"🗓️ Date: {escape_markdown(game['date'])}\n"
            f"🕒 Time: {escape_markdown(game['time'])}\n"
            f"🎟️ Spots Available: {escape_markdown(str(game['spots_left']))}\n"
            f"🎟️ Ticket Price: {escape_markdown(f'€{float(game['price_per_person']):.2f}')}\n"
            f"[Register here]({generate_registration_link(game['game_id'])})\n\n"
        )

    global last_message_id
    try:
        if last_message_id:
            await telegram_bot.edit_message_text(chat_id=channel_id, message_id=last_message_id, text=message, parse_mode='MarkdownV2')
        else:
            sent_message = await telegram_bot.send_message(chat_id=channel_id, text=message, parse_mode='MarkdownV2')
            last_message_id = sent_message.message_id
            await telegram_bot.pin_chat_message(chat_id=channel_id, message_id=sent_message.message_id)
            logging.info("Pinned the announcement message.")
    except Exception as e:
        logging.error(f"Error sending or pinning message: {e}")

async def monitor_game_updates():
    """Monitor games.csv file for updates every 30 minutes and update the announcement."""
    load_games()
    await send_game_announcements()

async def main():
    """Main entry point for the bot."""
    load_games()

    # Initialize the bot application
    app = Application.builder().token(telegram_bot_token).build()
    await app.initialize()
    await send_game_announcements()

    # Schedule the game updates every 30 minutes
    scheduler = AsyncIOScheduler()
    scheduler.add_job(monitor_game_updates, 'interval', minutes=5)
    scheduler.start()

    await app.start()
    logging.info("Bot is now online!")

    # Keep the bot running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
