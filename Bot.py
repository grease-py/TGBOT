import logging
import asyncio
import aiohttp
from decimal import Decimal
from datetime import datetime
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
HELIUS_API_ENDPOINT = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# Function to fetch top token holders using Helius API
async def fetch_token_holders(token_mint: str) -> list:
    url = HELIUS_API_ENDPOINT
    all_owners = set()
    cursor = None

    async with aiohttp.ClientSession() as session:
        while True:
            params = {
                "limit": 1000,
                "mint": token_mint
            }
            if cursor:
                params["cursor"] = cursor

            async with session.post(url, json={
                "jsonrpc": "2.0",
                "id": "helius-test",
                "method": "getTokenAccounts",
                "params": params
            }) as response:
                data = await response.json()

            if not data['result'] or len(data['result']['tokenAccounts']) == 0:
                logger.info("No more results")
                break

            for account in data['result']['tokenAccounts']:
                all_owners.add(account['owner'])

            cursor = data['result'].get('cursor', None)
            if cursor is None:
                break

    return list(all_owners)[:100]  # Return top 100 holders

# Function to fetch wallet transactions (use your existing logic)
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

# Function to calculate win rate (use your existing logic)
def calculate_win_rate(transactions):
    wins, total_trades = 0, 0
    token_balances = {}

    for tx in transactions:
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

# Bot handler function to analyze token holders
def analyze_token(update, context):
    token_address = update.message.text.strip()

    update.message.reply_text(f"Fetching top 100 holders for token {token_address}...")

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        top_holders = loop.run_until_complete(fetch_token_holders(token_address))
        loop.close()

    except Exception as e:
        logger.error(f"Error fetching top holders: {e}")
        update.message.reply_text(f"Error fetching top holders for token {token_address}.")
        return

    if not top_holders:
        update.message.reply_text(f"No holders found for token {token_address}.")
        return

    win_rates = []
    for holder in top_holders:
        try:
            data = loop.run_until_complete(fetch_all_transactions(holder))
            if data:
                overall_wins, overall_trades = calculate_win_rate(data)
                if overall_trades > 0:
                    win_rates.append(overall_wins / overall_trades * 100)
        except Exception as e:
            logger.error(f"Error fetching wallet data for holder {holder}: {e}")
            continue

    if win_rates:
        average_win_rate = sum(win_rates) / len(win_rates)
        update.message.reply_text(f"Average win rate for top 100 holders: {average_win_rate:.2f}%")
    else:
        update.message.reply_text("No valid win rates found for the top 100 holders.")

# Bot start and error handlers
def start(update, context):
    update.message.reply_text('Welcome! Paste a Solana token address to analyze its top holders.')

def error_handler(update, context):
    logger.warning(f'Update {update} caused error {context.error}')

# Main bot logic
def main():
    updater = Updater(os.getenv("TG"), use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, analyze_token))
    dp.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
