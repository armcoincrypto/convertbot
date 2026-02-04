"""Telegram Bot with Dash to TRON support."""
import asyncio
import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from app.db import txid_exists, get_txid_owner
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from app.config import settings
from libs.explorer_client import explorer_client
from app.models import CoinType
import aiosqlite
import re

# Configure logging - reduce httpx spam
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

CHOOSING_COIN, WAITING_TXID, WAITING_ADDRESS = range(3)

DEPOSIT_ADDRESSES = {
    "BTC": "33vFCeDJXdEPTnWFEyy5tRy85iQo1oBtw4",
    "LTC": "ltc1qdx26fhhma5x0kwld5l0dxrwc0mrcygl6fnvnxp",
    "DASH": "Xdiuzho4EhWWzEEDbNzbxYpt55DRDETgD9",
    "XMR": "88jVTyDDAJzWyaamiGWaAyXn487o53v7hgzPY46qAwBEBCJsvXoBVadgq1yj7kuBrD6sKo3v49twPCtJ5vozbTqW3HMqWb7",
    "USDT": "TFqUpY6Xnk6QLaHxBr5hTnuHLfAPgLMLQF",
}

COIN_INFO = {
    "BTC": {"name": "Bitcoin", "network": "Bitcoin", "confs": 2, "to": "USDT"},
    "LTC": {"name": "Litecoin", "network": "Litecoin", "confs": 4, "to": "USDT"},
    "DASH": {"name": "Dash", "network": "Dash", "confs": 12, "to": "USDT"},
    "DASH_TRX": {"name": "Dash", "network": "Dash", "confs": 12, "to": "TRX"},
    "XMR": {"name": "Monero", "network": "Monero", "confs": 10, "to": "USDT"},
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Clear any previous conversation data
    context.user_data.clear()

    keyboard = [
        [KeyboardButton("Bitcoin -> USDT"), KeyboardButton("Litecoin -> USDT")],
        [KeyboardButton("Dash -> USDT"), KeyboardButton("Dash -> TRON")],
        [KeyboardButton("Monero -> USDT")],
        [KeyboardButton("Check Status")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Welcome to Conod Bot!\n\n"
        "Minimum: $20 USD\n"
        "Fee: 3% + $1\n\n"
        "Select exchange type:",
        reply_markup=reply_markup
    )
    return CHOOSING_COIN

async def coin_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # Check if user clicked "Check Status"
    if "Check" in text or "Status" in text:
        await check_transaction(update, context)
        return ConversationHandler.END

    coin = None
    output_coin = "USDT"
    coin_key = None

    if "Bitcoin" in text:
        coin = "BTC"
        output_coin = "USDT"
        coin_key = "BTC"
    elif "Litecoin" in text:
        coin = "LTC"
        output_coin = "USDT"
        coin_key = "LTC"
    elif "Dash" in text and "TRON" in text:
        coin = "DASH"
        output_coin = "TRX"
        coin_key = "DASH_TRX"
    elif "Dash" in text and "USDT" in text:
        coin = "DASH"
        output_coin = "USDT"
        coin_key = "DASH"
    elif "Monero" in text:
        coin = "XMR"
        output_coin = "USDT"
        coin_key = "XMR"

    if not coin:
        await update.message.reply_text("Please select from the buttons above or /start to restart.")
        return CHOOSING_COIN

    context.user_data["coin"] = coin
    context.user_data["output_coin"] = output_coin
    context.user_data["coin_key"] = coin_key

    info = COIN_INFO[coin_key]
    address = DEPOSIT_ADDRESSES[coin]

    keyboard = [[KeyboardButton("I have sent")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        f"Your deposit address:\n\n"
        f"<code>{address}</code>\n\n"
        f"You selected: {info['name']} -> {output_coin}\n"
        f"Network: {info['network']}\n"
        f"Confirmations: {info['confs']}\n"
        f"Fee: 3%\n"
        f"Time: 20-30 minutes\n\n"
        f"After sending, click 'I have sent'.",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    return WAITING_TXID

async def waiting_for_txid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "I have sent" in text or "sent" in text.lower():
        await update.message.reply_text(
            "Please send the transaction HASH (64 characters):\n\n"
            "Example:\n"
            "<code>a65b33369cf0bcd1b4e7a47f00e6536612210aeb0ddb4e6ac557c9f83d316545</code>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
        return WAITING_TXID

    clean_text = text.strip().lower()
    if re.match(r"^[a-f0-9]{64}$", clean_text):
        # Check if TXID already exists
        async with aiosqlite.connect("swapbot.db") as conn:
            async with conn.execute("SELECT txid FROM deposits WHERE txid = ?", (clean_text,)) as cursor:
                existing = await cursor.fetchone()

        if existing:
            await update.message.reply_text(
                "This transaction has already been used.\n\n"
                "Please send a NEW transaction HASH.",
                parse_mode="HTML"
            )
            return WAITING_TXID

        context.user_data["txid"] = clean_text
        output_coin = context.user_data.get("output_coin", "USDT")

        network = "TRC20" if output_coin in ["USDT", "TRX"] else "Tron"

        await update.message.reply_text(
            f"TXID received!\n\n"
            f"<code>{clean_text[:32]}\n{clean_text[32:]}</code>\n\n"
            f"Now please send your {output_coin} ({network}) receiving address:\n\n"
            f"Example:\n"
            f"<code>TVQXrLPpULB6y4KnJMyZorxWQqR7UhhL3g</code>",
            parse_mode="HTML"
        )
        return WAITING_ADDRESS
    else:
        await update.message.reply_text(
            "Invalid format.\n\n"
            "TXID must be 64 characters (0-9, a-f).",
            parse_mode="HTML"
        )
        return WAITING_TXID

async def address_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text.strip()
    user_id = update.message.from_user.id

    if not (address.startswith("T") and len(address) == 34):
        await update.message.reply_text(
            "Invalid address.\n\n"
            "TRC20 address must start with T and be 34 characters.",
            parse_mode="HTML"
        )
        return WAITING_ADDRESS

    coin = context.user_data.get("coin")
    txid = context.user_data.get("txid")

    if not coin or not txid:
        await update.message.reply_text("Session expired. Please /start again.")
        context.user_data.clear()
        return ConversationHandler.END

    # Check if TXID already used
    if await txid_exists(txid):
        owner_id = await get_txid_owner(txid)
        if owner_id == user_id:
            await update.message.reply_text("This transaction has already been used by you.")
        else:
            await update.message.reply_text("This transaction has already been used by another user.")
        context.user_data.clear()
        return ConversationHandler.END

    output_coin = context.user_data.get("output_coin", "USDT")
    coin_key = context.user_data.get("coin_key")

    async with aiosqlite.connect("swapbot.db") as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO users (user_id, usdt_trc20_address) VALUES (?, ?)",
            (user_id, address)
        )

        info = COIN_INFO[coin_key]
        target_address = address

        await conn.execute(
            """INSERT OR IGNORE INTO deposits
               (txid, coin, user_id, status, confs, required_confs, target_address, output_coin)
               VALUES (?, ?, ?, 'NEW', 0, ?, ?, ?)""",
            (txid, coin, user_id, info['confs'], target_address, output_coin)
        )
        await conn.commit()

    keyboard = [[KeyboardButton("/start"), KeyboardButton("Check Status")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"Saved {output_coin} address:\n"
        f"<code>{address}</code>\n\n"
        f"Starting to check your transfer.\n\n"
        f"Transaction details:\n"
        f"TXID: <code>{txid[:16]}...{txid[-8:]}</code>\n"
        f"{info['name']} -> {output_coin}\n"
        f"Confirmations: 0/{info['confs']}\n\n"
        f"Please wait...\n"
        f"You will receive notifications here.",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

    context.user_data.clear()
    return ConversationHandler.END

async def check_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check user's transaction status"""
    user_id = update.effective_user.id

    async with aiosqlite.connect("swapbot.db") as conn:
        async with conn.execute(
            "SELECT txid, coin, status, confs, required_confs, onchain_amount, output_coin FROM deposits WHERE user_id = ? ORDER BY inserted_at DESC LIMIT 5",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        await update.message.reply_text(
            "No transactions found.\n"
            "Click /start to begin."
        )
        return ConversationHandler.END

    message = "Your recent transactions:\n\n"

    for row in rows:
        status_emoji = {
            'NEW': 'NEW',
            'CONFIRMING': 'CONFIRMING',
            'CONFIRMED': 'CONFIRMED',
            'SOLD': 'SOLD',
            'WITHDRAWN': 'DONE',
            'TRADE_FAILED': 'FAILED',
            'PROCESSING_ERROR': 'ERROR',
        }.get(row[2], row[2])

        message += f"{row[1]} -> {row[6] or 'USDT'}\n"
        message += f"   Status: {status_emoji}\n"
        message += f"   Confs: {row[3]}/{row[4]}\n"
        if row[5]:
            message += f"   Amount: {row[5]:.4f}\n"
        message += "\n"

    await update.message.reply_text(message)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Cancelled. /start to begin again.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown commands or messages"""
    await update.message.reply_text(
        "Unknown command.\n\n"
        "Contact support: @Conodoperatorbot\n\n"
        "Or click /start for new exchange."
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the bot."""
    logger.error(f"Exception while handling update: {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "An error occurred. Please try /start again."
            )
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

async def timeout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle conversation timeout"""
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Session timed out. Please /start again."
        )
    return ConversationHandler.END

def main():
    application = Application.builder().token(settings.telegram_bot_token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_COIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, coin_chosen)],
            WAITING_TXID: [MessageHandler(filters.TEXT & ~filters.COMMAND, waiting_for_txid)],
            WAITING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, address_received)],
            ConversationHandler.TIMEOUT: [MessageHandler(filters.ALL, timeout_handler)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
        ],
        conversation_timeout=600,  # 10 minute timeout
        per_user=True,
        per_chat=True,
    )

    application.add_handler(conv_handler)

    # Handler for check commands
    application.add_handler(CommandHandler("status", check_transaction))
    application.add_handler(CommandHandler("check", check_transaction))

    # Handler for check button (outside conversation)
    application.add_handler(MessageHandler(
        filters.Regex("(?i)check|status") & ~filters.COMMAND,
        check_transaction
    ))

    # Catch-all for unknown messages (must be last)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        unknown_command
    ))

    # Error handler
    application.add_error_handler(error_handler)

    print("Bot starting...")
    print("Supported swaps:")
    print("   Bitcoin -> USDT")
    print("   Litecoin -> USDT")
    print("   Dash -> USDT")
    print("   Dash -> TRON")
    print("   Monero -> USDT")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
