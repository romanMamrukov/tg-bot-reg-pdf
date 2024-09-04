# Telegram Bot to register users and provide invoice summary of registration

This Telegram bot assists users with registration and provides a summary of their registrations, including generating a PDF invoice.

## Features

- Multi-language support.
- Registration process with prompts for first name, last name, email, and the number of attendees.
- Generates a PDF invoice based on the registration details.
- Ability to retrieve and view previous registrations.

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

### 4. Set Up Environment Variables
Modify a .env file in the project root directory to store your bot token:

```bash
BOT_TOKEN=your-telegram-bot-token
```

Alternatively, you can directly replace the token in the main() function of your script.

### 5. Prepare the Project Directory
Ensure that the following directory is created for storing PDF invoices:

```bash
mkdir invoice_store
```

### 6. Run the Bot
Execute the bot using the following command:

```bash
python testbot.py
```

The bot will start running and listening for user interactions.

### 7. Using the Bot
Start a conversation with the bot by typing /start.
Follow the prompts to register your information.
The bot will generate a PDF invoice and send it back to you in the chat, as well as store it in the specified directory.
Retrieve previous registrations by typing /retrieve.

### 8. Deployment
To deploy the bot, you may consider using services like Heroku, AWS Lambda, or any other cloud platform that supports Python applications.

### Acknowledgements
* python-telegram-bot for the Telegram API.
* ReportLab for PDF generation.
