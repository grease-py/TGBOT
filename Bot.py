import logging
import asyncio
import aiohttp
from decimal import Decimal
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import os
import time

# Try to load dotenv, but don't fail if it's not available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Helius API endpoint and API Key
HELIUS_API_KEY = os.getenv('HELIUS')
HELIUS_API_ENDPOINT = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# List of FATGF wallet addresses
wallet_addresses = [
    "FdN14TTEjpbdj2kLT4fBsgWNGdw26zJGWwnej83via1E",
    "3du5jorAF6YUcnpTntWdwRUNVrWs1i7zfi3fs1ahNB6n",
    # Add the rest of the addresses here
]

# A list to store the win rates and keep track of the last 100 scanned wallets
winrate_log = []

# Function to fetch wallet transactions using Helius API
async def fetch_all_transactions(wallet_address: str) -> list:
    async with aiohttp.ClientSession() as session:
        all_transactions = []
        before = None
        while True:
            url = f"{HELIUS_API_ENDPOINT}/{wallet_address}/transactions?limit=100"
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
            
            logger.info(f"Fetched {len(all_transactions)} transactions so far...")
        
        logger.info(f"Total transactions fetched: {len(all_transactions)}")
        return all_transactions

# Function to calculate win rate
def calculate_win_rate(transactions):
    wins, total_trades = 0, 0
    token_balances = {}

    for tx in transactions:
        token = tx.get('tokenName')
        if tx.get('isSell'):
            if token in token_balances and token_balances[token]['amount'] > 0:
                if tx['amount'] <= token_balances[token]['amount']:
                    wins += 1
                total_trades += 1
                token_balances[token]['amount'] -= tx['amount']
        else:
            if token not in token_balances:
                token_balances[token] = {'amount': 0}
            token_balances[token]['amount'] += tx['amount']

    return wins, total_trades

# Function to log the win rate of each wallet and keep track of the last 100
async def analyze_fatgf(update, context):
    if update.message.text.lower() == "fatgf":
        win_rates = []
        
        for wallet_address in wallet_addresses:
            try:
                # Fetch the transactions for each wallet
                transactions = await fetch_all_transactions(wallet_address)
                if transactions:
                    overall_wins, overall_trades = calculate_win_rate(transactions)
                    if overall_trades > 0:
                        win_rate = overall_wins / overall_trades * 100
                        win_rates.append(win_rate)

                        # Add to winrate_log
                        winrate_log.append(win_rate)
                        logger.info(f"Logged win rate {win_rate:.2f}% for {wallet_address}")

                        # Ensure we only keep the last 100 entries in the log
                        if len(winrate_log) > 100:
                            winrate_log.pop(0)

                # Delay between each request to avoid API overload
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"Error fetching wallet data for {wallet_address}: {e}")
                continue

        # Calculate the average win rate
        if win_rates:
            average_win_rate = sum(win_rates) / len(win_rates)
            update.message.reply_text(f"Average win rate for FATGF wallets: {average_win_rate:.2f}%")
        else:
            update.message.reply_text("No valid win rates found for FATGF wallets.")
    else:
        update.message.reply_text("Invalid command. Please send 'fatgf' to calculate the average win rate.")

# Function to calculate the average win rate of the last 100 scanned wallets
def last100(update, context):
    if len(winrate_log) > 0:
        average_last100 = sum(winrate_log) / len(winrate_log)
        update.message.reply_text(f"Average win rate for the last {len(winrate_log)} wallets: {average_last100:.2f}%")
    else:
        update.message.reply_text("No wallets have been scanned yet.")

# Modify the message handler to listen for "fatgf" and "/last100"
def main():
    updater = Updater(os.getenv("TG"), use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("last100", last100))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, analyze_fatgf))
    dp.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
