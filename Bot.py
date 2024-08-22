import logging
import re
import asyncio
import json
from decimal import Decimal
from datetime import datetime, timedelta
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Helius API endpoint and API Key
HELIUS_API_KEY = os.getenv('HELIUS')
HELIUS_API_ENDPOINT = "https://api.helius.xyz/v0/addresses"

# Define a simple regex for wallet address validation
wallet_address_pattern = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Welcome! Please paste a Solana wallet address to analyze.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Paste a Solana wallet address to get its analysis.')

async def fetch_all_transactions(wallet_address: str) -> list:
    async with aiohttp.ClientSession() as session:
        all_transactions = []
        before = None
        while True:
            url = f"{HELIUS_API_ENDPOINT}/{wallet_address}/transactions?api-key={HELIUS_API_KEY}&limit=100"
            if before:
                url += f"&before={before}"
            
            async with session.get(url) as response:
                transactions = await response.json()
                
            if not transactions:
                break
            
            all_transactions.extend(transactions)
            
            if len(transactions) < 100:
                break
            
            before = transactions[-1]['signature']
            
            # Log progress
            logger.info(f"Fetched {len(all_transactions)} transactions so far...")
        
        logger.info(f"Total transactions fetched: {len(all_transactions)}")
        return all_transactions

# The rest of your functions (fetch_wallet_data, calculate_win_rate, analyze_wallet) remain the same

def main() -> None:
    application = Application.builder().token(os.getenv("TG")).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze_wallet))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
