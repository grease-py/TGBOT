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
