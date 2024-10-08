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
    update.message.reply_text('Welcome! Please paste a Solana wallet address to analyze.')

def help_command(update, context):
    update.message.reply_text('Paste a Solana wallet address to get its analysis.')

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
    wallet_address = update.message.text.strip()
    
    if not wallet_address_pattern.match(wallet_address):
        update.message.reply_text("Invalid wallet address format. Please try again.")
        return

    update.message.reply_text("Analyzing wallet... This may take a while for wallets with many transactions.")
    
    try:
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the asynchronous function
        data = loop.run_until_complete(fetch_wallet_data(wallet_address))
        
        # Close the event loop
        loop.close()
    except Exception as e:
        logger.error(f"Error fetching wallet data: {e}")
        update.message.reply_text("An error occurred while fetching wallet data. Please try again.")
        return

    if not data:
        update.message.reply_text("No data found for this wallet. Please try again.")
        return

    transactions = data['transactions']
    
    now = int(datetime.now().timestamp())
    one_month_ago = int((datetime.now() - timedelta(days=30)).timestamp())
    one_week_ago = int((datetime.now() - timedelta(days=7)).timestamp())
    
    overall_wins, overall_trades = calculate_win_rate(transactions)
    monthly_wins, monthly_trades = calculate_win_rate(transactions, one_month_ago, now)
    weekly_wins, weekly_trades = calculate_win_rate(transactions, one_week_ago, now)

    overall_win_rate = (overall_wins / overall_trades * 100) if overall_trades > 0 else 0
    monthly_win_rate = (monthly_wins / monthly_trades * 100) if monthly_trades > 0 else 0
    weekly_win_rate = (weekly_wins / weekly_trades * 100) if weekly_trades > 0 else 0

    # Create a hyperlink to the wallet address on DexCheck wallet analyzer
    wallet_link = f"https://dexcheck.ai/app/wallet-analyzer/{wallet_address}"

    analysis = f"""
Wallet Analysis for <a href="{wallet_link}">{wallet_address}</a>

Win Rates:
Overall: {overall_win_rate:.2f}% ({overall_wins}/{overall_trades} trades)
Last 30 days: {monthly_win_rate:.2f}% ({monthly_wins}/{monthly_trades} trades)
Last 7 days: {weekly_win_rate:.2f}% ({weekly_wins}/{weekly_trades} trades)

Total Transactions Analyzed: {len(transactions)}
    """

    # Send the message with the hyperlink
    update.message.reply_html(analysis, disable_web_page_preview=True)


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
