import logging
import re
import asyncio
import json
from decimal import Decimal
from datetime import datetime, timedelta
import aiohttp
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import os

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
HELIUS_API_ENDPOINT = "https://api.helius.xyz/v0/addresses"

# Define a simple regex for wallet address validation
wallet_address_pattern = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')

def start(update, context):
    update.message.reply_text('Welcome! Please paste up to 100 Solana wallet addresses (separated by space or newline) to analyze.')

def help_command(update, context):
    update.message.reply_text('Paste up to 100 Solana wallet addresses to get their analysis.')

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

async def fetch_wallet_data(wallet_address: str) -> dict:
    try:
        transactions = await fetch_all_transactions(wallet_address)
        
        processed_transactions = []
        for tx in transactions:
            signature = tx.get('signature', '')
            block_time = tx['timestamp']
            
            for event in tx.get('tokenTransfers', []):
                if event['fromUserAccount'] == wallet_address:
                    # Sell transaction
                    token_name = event['mint']
                    amount = Decimal(event['tokenAmount'])
                    processed_transactions.append({
                        'signature': signature,
                        'blockTime': block_time,
                        'tokenName': token_name,
                        'amount': amount,
                        'isSell': True
                    })
                elif event['toUserAccount'] == wallet_address:
                    # Buy transaction
                    token_name = event['mint']
                    amount = Decimal(event['tokenAmount'])
                    processed_transactions.append({
                        'signature': signature,
                        'blockTime': block_time,
                        'tokenName': token_name,
                        'amount': amount,
                        'isSell': False
                    })

        return {
            'wallet_address': wallet_address,
            'transactions': processed_transactions
        }

    except Exception as e:
        logger.error(f"Error fetching wallet data: {e}")
        return None

def calculate_win_rate(transactions, start_time=None, end_time=None):
    if start_time is None:
        start_time = 0
    if end_time is None:
        end_time = float('inf')
    
    filtered_transactions = [tx for tx in transactions if start_time <= tx['blockTime'] <= end_time]
    
    token_balances = {}
    wins = 0
    total_trades = 0
    
    for tx in filtered_transactions:
        token = tx['tokenName']
        if tx['isSell']:
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

def analyze_wallet(update, context):
    addresses = update.message.text.strip().split()  # Split input by space or newline
    
    if len(addresses) > 100:
        update.message.reply_text("Please provide up to 100 addresses.")
        return

    win_rates = []
    total_transactions = 0

    for wallet_address in addresses:
        if not wallet_address_pattern.match(wallet_address):
            update.message.reply_text(f"Invalid address format for {wallet_address}. Skipping...")
            continue

        update.message.reply_text(f"Analyzing wallet {wallet_address}...")

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            data = loop.run_until_complete(fetch_wallet_data(wallet_address))
            loop.close()
        except Exception as e:
            logger.error(f"Error fetching wallet data for {wallet_address}: {e}")
            continue

        if not data:
            update.message.reply_text(f"No data found for wallet {wallet_address}. Skipping...")
            continue

        transactions = data['transactions']
        overall_wins, overall_trades = calculate_win_rate(transactions)

        if overall_trades > 0:
            win_rates.append(overall_wins / overall_trades * 100)
        total_transactions += len(transactions)

    # Calculate the average win rate
    if win_rates:
        average_win_rate = sum(win_rates) / len(win_rates)
        update.message.reply_text(f"Average win rate for {len(addresses)} addresses: {average_win_rate:.2f}%")
    else:
        update.message.reply_text("No valid win rates found for the provided addresses.")

def error_handler(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main():
    updater = Updater(os.getenv("TG"), use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, analyze_wallet))
    dp.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
