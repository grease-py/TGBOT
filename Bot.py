import logging
import re
import asyncio
import json
from datetime import datetime, timedelta
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import os

# Load environment variables from 1.env
env_file_loaded = load_dotenv("1.env")

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
TG_BOT_TOKEN = os.getenv("TG")
HELIUS_API_KEY = os.getenv('HELIUS')

# Helius API endpoint for wallet data
HELIUS_API_ENDPOINT = "https://api.helius.xyz/v0/mainnet/new-wallets"

# Define a simple regex for wallet address validation
wallet_address_pattern = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')

# Start function for the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Welcome! You can use /check_wallets to check wallets created today.')

# Help function for the /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Use /check_wallets to fetch the wallets created today between 6:50 PM EST and 12:00 PM UTC.')

# Function to convert 6:50 PM EST to 12:00 PM UTC on the current day to UTC timestamps
def get_time_window():
    today = datetime.now()

    # Start time: 6:50 PM EST = 11:50 PM UTC
    start_time = today.replace(hour=18, minute=50, second=0, microsecond=0) + timedelta(hours=4)  # Convert to UTC

    # End time: 12:00 PM UTC
    end_time = today.replace(hour=12, minute=0, second=0, microsecond=0)  # 12:00 PM UTC

    # Convert to UNIX timestamps
    start_timestamp = int(start_time.timestamp())
    end_timestamp = int(end_time.timestamp())

    logger.info(f"Start Time: {start_time}, End Time: {end_time}")
    logger.info(f"Start Timestamp: {start_timestamp}, End Timestamp: {end_timestamp}")

    return start_timestamp, end_timestamp

# Fetch new wallets around the given time window
async def fetch_new_wallets() -> list:
    start_time, end_time = get_time_window()

    url = f"{HELIUS_API_ENDPOINT}?api-key={HELIUS_API_KEY}&start_time={start_time}&end_time={end_time}"
    
    logger.info(f"Fetching wallets with URL: {url}")

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                logger.error(f"Failed to fetch new wallets. Status: {response.status}, Response: {await response.text()}")
                return []

            wallets = await response.json()

    logger.info(f"Response from Helius API: {json.dumps(wallets, indent=2)}")
    logger.info(f"Fetched {len(wallets)} wallets created in the time window.")
    
    return wallets

# Function to handle the /check_wallets command
async def check_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Executing /check_wallets command")

    await update.message.reply_text("Fetching new wallets created between 6:50 PM EST and 12:00 PM UTC today...")

    wallets = await fetch_new_wallets()

    if wallets:
        wallet_list = "\n".join(wallets)
        await update.message.reply_text(f"New wallets created:\n{wallet_list}")
    else:
        await update.message.reply_text("No new wallets were created within the specified time range.")

# Main function to run the bot
def main() -> None:
    if not TG_BOT_TOKEN:
        logger.error("Bot token is missing or invalid!")
        return
    
    application = Application.builder().token(TG_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("check_wallets", check_wallets))  # Add check_wallets command

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()