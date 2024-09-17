# Telegram Bots for Games announcements and to register users, provide invoice summary of registration

## Overview
This repository contains two Telegram bots: 
1. **Announcement Bot**: Announces upcoming games and provides deeplinks for registration.
2. **Registration Bot**: Handles user registration, game details summary, and generates PDF invoices.

## Features

### Announcement Bot
- **Announces Games**: Posts games happening within 7 days to a Telegram channel.
- **Deeplink Generation**: Each game announcement includes a deeplink to register for the game via the Registration Bot.

### Registration Bot
- **User Registration**: Registers users for games with details like name, email, and number of attendees.
- **Language Selection**: Supports multiple languages (English, Latvian, Russian).
- **Game Summary Posting**: Posts game details before and after registration.
- **PDF Invoice Generation**: Generates a PDF with registration details and sends it to both the user and an admin group.
- **User Data Handling**: Saves and retrieves user registration data from `user_data.json`.
- **Game Spots Update**: Automatically updates the `games.csv` file with remaining spots after registration.

## Prerequisites

- **Python 3.8 or later**: Ensure you have Python installed. You can download it from the official [Python website](https://www.python.org/downloads/).
- **Telegram Bot Token**: Obtain a bot token from [BotFather](https://core.telegram.org/bots#botfather) on Telegram.

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

### Activate the virtual environment:

### Windows:

```bash
venv\Scripts\activate
```

### macOS/Linux:

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

- games.csv: Game information.
- translations.json: Language translations for the bot.
- user_data.json: Stores user registration data.

### 5. Set Up Environment Variables
Modify a .env file in the project root directory to store your bot token:

```bash
BOT_TOKEN=your-telegram-bot-token
```

Alternatively, you can directly replace the token in the main() function of your script.

### 6. Prepare the Project Directory
Ensure that the following directory is created for storing PDF invoices:

```bash
mkdir invoice_store
```

### 6. Run the Bots

### Run the Announcement Bot:

```bash
python anno_bot1.py
```

### Run the Registration Bot:

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
- Implement registration cancellation.
- Add payment link generation and payment confirmation.
- Add reminders for payments and upcoming games.
