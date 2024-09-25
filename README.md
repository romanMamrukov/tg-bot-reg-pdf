# Telegram Game Management Bot Suite

This repository contains two Telegram bots designed to streamline game management for your events.

## Bot Suite Components
1. **Telegram Game Announcement Bot (`anno_bot1.py`)**
   This bot automatically generates and posts announcements for upcoming games on your Telegram channel. It fetches game information from a CSV file and sends a combined announcement for all upcoming games within the next 7 days.
2. **Telegram Game Registration Bot (`reg_bot1.py`)**
   This bot handles game registrations, generates PDF invoices, and integrates with Stripe for payment processing. Users can register for games directly through the bot, receive registration summaries, and manage their registrations.

## Features

**Game Announcement Bot:**

- Automatic Game Announcements
- Deeplinking for Registration
- Real-time Updates
- Message Pinning
- Markdown Support

**Game Registration Bot:**

- Registration Handling
- PDF Invoice Generation
- Payment Integration (Stripe)
- Language Support
- Registration Summary
- Game Spot Management
- Cancelation Functionality
- Email Notifications

## Prerequisites

- **Python 3:** The bots are written in Python and require Python 3 to be installed.
- **Telegram Bot Tokens:** Obtain bot tokens from BotFather on Telegram for both bots.
- **Telegram Channel IDs:** Get your Telegram channel IDs for both bots.
- **Stripe API Key:** (For the Game Registration Bot) Create a Stripe account and obtain your API key.

- **CSV File:** Create a CSV file named `games.csv` in the `store` directory with the following columns:

   | Column Name | Description |
   |---|---|
   | `game_id` | Unique identifier for the game |
   | `game_name` | Name of the game |
   | `description` | Brief description of the game |
   | `place` | Location of the game |
   | `date` | Date of the game (YYYY-MM-DD format) |
   | `time` | Time of the game (HH:MM format) |
   | `spots_all` | Total number of spots available |
   | `spots_left` | Number of spots available |
   | `price_per_person` | Price per person |

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/telegram-bot-pdf.git
cd telegram-bot-pdf
```

### 2. Create a Virtual Environment
It's recommended to use a virtual environment to manage your project's dependencies:
```bash
python -m venv venv
```

Activate the virtual environment:
Windows:
```bash
venv\Scripts\activate
```

macOS/Linux:
```bash
source venv/bin/activate
```

### 3. Install Dependencies
Install the necessary Python packages using pip:

```bash
pip install -r requirements.txt
```
If the requirements.txt file is not available, install the required packages manually:

```bash
pip install python-telegram-bot==20.0 reportlab
```
### 4. Create the required files:
games.csv: Game information.
translations.json: Language translations for the bot.
user_data.json: Stores user registration data.

### 5. Set Up Environment Variables
Create a .env file in the project root directory to store your bot tokens and other credentials:

*** Game Announcement Bot:

BOT_TOKEN_ANNO=YOUR_BOT_TOKEN
CHANNEL_ID_ANNO=YOUR_CHANNEL_ID

*** Game Registration Bot:

BOT_TOKEN=YOUR_BOT_TOKEN
CHANNEL_ID=YOUR_CHANNEL_ID
STRIPE_SECRET_KEY=YOUR_STRIPE_API_KEY
EMAIL_HOST=YOUR_EMAIL_HOST
EMAIL_USER=YOUR_EMAIL_USERNAME
EMAIL_PASSWORD=YOUR_EMAIL_PASSWORD
ADMIN_EMAIL=YOUR_ADMIN_EMAIL

### 6. Prepare the Project Directory
Ensure that the following directory is created for storing PDF invoices:

```bash
mkdir invoice_store
```

### 7. Run the Bots
Run the Announcement Bot:
```bash
python anno_bot1.py
```

Run the Registration Bot:
```bash
python reg_bot1.py
```

### Files
- anno_bot1.py: Handles game announcements and deeplink generation.
- reg_bot1.py: Handles user registration, language selection, PDF generation, and user data storage.
- games.csv: Stores game details like game_id, game_name, date, spots_left.
- translations.json: Contains language translations for bot messages.
- user_data.json: Stores user registration details.
- pdf_invoice.py: Script for generating PDF invoices for user registrations.

### To-Do

- Add payment confirmation.
- Add reminders for payments and upcoming games.
- Translations to Games announcements, Emails summary, Data retrieve
- Edit Payment checkout

### Contributing
Contributions are welcome! Feel free to open an issue or submit a pull request.
