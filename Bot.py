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
    "7Q8YFg2tDYikRckuessj2WoJjRad1cmhvEQnHGJ1f8Wd",
    "Ent3Q9z7Zx7FKn5WFaUAp6at7aedJLAg6p8BV3Nj63f6",
    "4FxsfMpZr9hdYgPaZYdBgrfAcruoLaodb5zQAQ8niSY2",
    "828eqpoUJTp3TxRnn3u8eXt7dmVfLWKqWDcTZXrp9LUe",
    "8Ga6pH8cpxspHEeF9Q3nc6BTgHCxnMwMJvvvecErLux7",
    "AnNoZKcv7vrhp3jKp9bGM6xDitJ6xkmJmzacbGH7bRq7",
    "G4HEkQA1NMSYbU8eHy6KsP6vz281Y3qV9HfrLWkjmcN1",
    "7VopARur3tQe3pNyyHxZfgmyccmtMDPze8ULLx8uiuhR",
    "Gaa6M9fbv2gQUEvaeD5Tckfyd2WPZ9VUbtX2huV3TKpt",
    "43MbGpTjwnKwpPE7TSWmQWmokvbQ6CxQGjfVuwCwZKAP",
    "H6azfrDwWFmQav8UMLiofEi73q6uZVv9geNqpy6VQXV9",
    "FB5xQkba9mJrU4riGMPB4XbS2tpokPSxg283CZVmw6Re",
    "BHXWj3UQPMNyYAgxwBWhfcEzme1gBzuJuC18hS7dqRKf",
    "HB8qenSVVYbK9tzkQRdXrPd5bzJfBm96wm6ehrLWcR9Q",
    "BYvV3SPzHKA81PBaS6Y9SvAAtrwaRQG6EZNcLdgBxHgG",
    "3ueTNaVJVXf3qwg6ZZDcwcxp6BbbUJCakovw3bWeGmX6",
    "2zJm81kN44vxkBMrnBxv2qZoX5ckU3jcFKj73mWxPvXp",
    "9p56ek1Sragtmbj1NvJWMSDxCHLcUEfzYZ9VvovYbLn8",
    "B8g2Gz9GdjWESxE2EgySUuCqLjWJsVN2NvRaAkBXogNJ",
    "3u3Ab132ZSHEhxossTkpDzjEWd3jvU7YjS4vG9TKwQZV",
    "8o8BBdC8PBs3EDLBjwBYFmUAke8F4Ej2CQCpkSkZ36m3",
    "Do3tVcTz66g93DPP5hXohzCKR2ByJoiGoXtchifRqyHv",
    "6wrcLYzmMSDfcNEndvtkxdtShd9FDZyKR5ULX8Zj9XM9",
    "3Wr4VeBHcHUQGgnW1tLcVVBfDWRCjuRDGJ5dnFQtQ3mg",
    "Gc2aAiy14jT3cE9RZwEK8y36D49YB4eeVr3E9amgDn7f",
    "GiiQU85i1y428kBxNQqZBztgSLGbUgo8eGVWnDRH3uNK",
    "9vuf62XM3nf1TqceYYfd5RUawZ1rvmVYJJRmhc5e9Lgt",
    "78jXi3osG92sSE39xkoEFgjeEDrFdS8qBhhNwAnnv6YK",
    "3u3v13ng5MCa8xb5HPAgKAERikteB8iqT2nRYDMVKdt6",
    "QcY1NXBp3emPA3MeCs5L1CveDjDnrnT8T9qDnLKx54Z",
    "G96msgCPqjAFZ4d8UX14KC7fhQ5WM4QjBnGyY1YgNtbs",
    "D1wMyKkyQPyqb5vQNGEnbXZCchaPDtDtFn3w2KVqzLNH",
    "DKmQngAhJkDoW982UBaQnjb6jpG7XqM4UMwNJZTvFW8t",
    "Aqp1FaGqtdQAG9A4YRGmgxGZcN9JF41erXDiv8ZUP1yw",
    "kHjyGkNjoGc5n7bAXrLnYLvSW2WdhNsgHgVBUKouUHd",
    "3YntPHQd9EJggSSNutbdkHgFTnFtyjyLDouF2Tu6uFSP",
    "Hhq83q7STAKH5QaLrxAtMKBLvBRSYpZJdanaKDLWiryD",
    "DbV2SYn457xSzvrEpab7YZZQ7LtJHp3xcvcW8P67zCXE",
    "2nG4yghLpx6t6z3CurJ5j1h4p78Mm177TtsK5AmcX1aq",
    "4esbmFRpSS7ceeRXhpW2FLCeGyaqJ448Zx7AMeced1pN",
    "4Nvi2KdNwnP7TL4ChCSgH99cLHPQv3nKPpziHFkJnF6q",
    "59fUqS4EdFeJcjNkZwZPsb8969cauDgPGgQ6ttwi4kK9",
    "C1TnzdK4nmbqWb3D7EMGBNoc4oHutjwz1SjETMm8wsuv",
    "nEEGqxZQvCxUck36k22DR9S8J4ABMXoEW32tnfJMptZ",
    "K9YLkgVmFDKCtbF3NvZz8kt1JMSWweF7Kz12mwZF32U",
    "EYrZQyFxC9nAJTdmy8f6bFxGvqkoe3WUFRzr7Fi4HtDi",
    "fent.sol",
    "4Nw8vPWCXMrSsAYw8TgjV8geVuKPZMi95uUusNCnzjME",
    "CcNqmhu2sRVmPbTvbP5iGgeWMSaNQpstfrg7nCDKyoj5",
    "2KCWYG5FoQ56M46F7BSvnouWQHMrYBuUZmTTxdQeiZVU",
    "2GHTuyDHmdi83AYKoxNxD7vh24CagzEPFFJ7hcC725km",
    "7YBxtkCwi4tLRXMdwCSkjwdaBdwLEvXYW4973qw7HGLe",
    "BCvYeeeehuPQ7gxGhzBjGTNEtCiSyPSbsKuCqapbSvVm",
    "Dw5kDRmrWYR2UxiobYLaQyPTn1ETPoy2xVbuVjG9qr5w",
    "hornyarc.sol",
    "Dgfg92cxKTP132dva461QX543gxT6CoADpmksHvWdWP2",
    "7wjz8otyFSjJ1p2HD1ucuFa5VheyNTYGcjGmp8mTCULE",
    "F5EHKx8beXnEQtnVfwURzrXtN2tRakC4ZBt9c7Dwwsmp",
    "soloxbt.sol",
    "2a2bryTPbYWu7F79fD3rMpt7Fg3AhbmkJh77oCGowJZ6",
    "7oaPXiGuKPhFRaKUp95gFZpZnNr9XinauXV7GrEbimiE",
    "CyF8YU2DbeE4Qn6Ze8J2PPuey

]

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

# Function to calculate the average win rate for FATGF wallets
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
                        win_rates.append(overall_wins / overall_trades * 100)

                # Delay between each request to avoid API overload
                await asyncio.sleep(2)  # Use asyncio.sleep for non-blocking delay

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

# Modify the message handler to listen specifically for "fatgf"
def main():
    updater = Updater(os.getenv("TG"), use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, analyze_fatgf))
    dp.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()