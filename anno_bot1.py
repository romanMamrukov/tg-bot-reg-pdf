import pandas as pd
import logging
import asyncio
import base64
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, CallbackContext
from urllib.parse import quote_plus


"""This bot works with announcments posting and scheduling as well as creating deeplink for the the registration"""
# Your Telegram bot token
telegram_bot_token = "YOUR_BOT_TOKEN"
channel_id = "@YOUR_CHANNEL_NAME"  # Replace with your Telegram channel name

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Telegram Bot
telegram_bot = Bot(token=telegram_bot_token)

def load_games(file_path):
    """Load game data from a CSV file."""
    try:
        logging.info("Loading game data...")
        games_df = pd.read_csv(file_path)
        games_df.columns = games_df.columns.str.strip()  # Clean column names

        # Ensure "spots" are numeric and clean the data
        games_df['price_per_person'] = pd.to_numeric(games_df['price_per_person'], errors='coerce').fillna(0).astype(int) 
        games_df['spots_all'] = pd.to_numeric(games_df['spots_all'], errors='coerce').fillna(0).astype(int)
        games_df['spots_registered'] = pd.to_numeric(games_df['spots_registered'], errors='coerce').fillna(0).astype(int)
        games_df['spots_left'] = pd.to_numeric(games_df['spots_left'], errors='coerce').fillna(0).astype(int)
        
        logging.info("Games data loaded successfully.")
        return games_df.to_dict(orient='records')
    except Exception as e:
        logging.error(f"Error loading game data: {e}")
        return []

async def send_game_announcements(games):
    """Send an announcement for games that are 7 days or less away, and today's games."""
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
    """Announce the game on Telegram."""
    # URL-encode the parameters
    game_id = game['game_id']
    
    # Telegram link to the second bot with query parameters
    def generate_registration_link(game_id):
        query = (
            f"game_id={quote_plus(game_id)}"
        )
        encoded_query = base64.urlsafe_b64encode(query.encode()).decode()  # Encode the query into base64
        registration_link = f"https://t.me/opengames_cc_pdf_bot?start={encoded_query}"
        return registration_link

    registration_link = generate_registration_link(game_id)

    # Use MarkdownV2 for proper Telegram link formatting
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
    # Announce on Telegram Channel
    await telegram_bot.send_message(chat_id=channel_id, text=message, parse_mode='MarkdownV2')
        
def escape_markdown(text):
    """Escape MarkdownV2 special characters."""
    if not isinstance(text, str):
        text = str(text)  # Ensure it's a string
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + char if char in escape_chars else char for char in text])

# Create bot application
app = Application.builder().token(telegram_bot_token).build()

def get_upcoming_games(period='month'):
    """Get games based on the selected period (month or year)."""
    today = datetime.now()

    if period == 'month':
        end_date = today + timedelta(days=30)
    elif period == 'year':
        end_date = today + timedelta(days=365)
    else:
        end_date = today + timedelta(days=7)

    return [
        game for game in games
        if today <= datetime.strptime(game['date'], "%Y-%m-%d") <= end_date
    ]

async def auto_announce_games():
    """Announce games immediately when the bot starts."""
    if games:
        await send_game_announcements(games)

# Scheduler to send announcements every 8 hours
def schedule_repeated_announcements():
    """Schedule announcements to check every 8 hours for games happening in 7 days or less."""
    scheduler = BackgroundScheduler()

    def repeated_game_announcements():
        """Function to announce games every 8 hours."""
        asyncio.run(send_game_announcements(games))

    # Schedule announcements every 8 hours
    scheduler.add_job(repeated_game_announcements, 'interval', hours=1)
    scheduler.start()
    logging.info("Scheduler started: announcing games every 1 hours.")

async def main():
    """Main entry point to start the bot and schedule announcements."""
    global games
    file_path = "games.csv"
    
    games = load_games(file_path)
    
    # Initialize the bot application
    if not app._running:
        await app.initialize()  # Add this line to initialize the bot application

    # If there are games, send announcements immediately and schedule them repeatedly
    if games:
        await auto_announce_games()
        schedule_repeated_announcements()

    # Start the bot in polling mode
    await app.start()

    # The bot will run indefinitely
    try:
        await asyncio.Event().wait()  # Keeps the bot running
    except KeyboardInterrupt:
        await app.stop()

if __name__ == '__main__':
    asyncio.run(main())
