"""Telegram Bot with i18n support and language detection."""
import asyncio
import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from app.db import txid_exists, get_txid_owner
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from app.config import settings, fee_display
from libs.explorer_client import explorer_client
from app.models import CoinType
from app.i18n import get_msg, resolve_lang
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


def get_user_msg(update):
    """Get MSG class for user's language."""
    lang = resolve_lang(update)
    return get_msg(lang)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - show coin selection."""
    context.user_data.clear()
    MSG = get_user_msg(update)

    keyboard = [
        [KeyboardButton(MSG.BTN_BTC_USDT), KeyboardButton(MSG.BTN_LTC_USDT)],
        [KeyboardButton(MSG.BTN_DASH_USDT), KeyboardButton(MSG.BTN_DASH_TRX)],
        [KeyboardButton(MSG.BTN_XMR_USDT)],
        [KeyboardButton(MSG.BTN_CHECK_STATUS)],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        MSG.welcome(),
        reply_markup=reply_markup
    )
    return CHOOSING_COIN


async def coin_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle coin selection."""
    text = update.message.text
    MSG = get_user_msg(update)

    # Check if user clicked "Check Status" (any language)
    if any(x in text.lower() for x in ["check", "status", "prover", "stugel"]):
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
        await update.message.reply_text(MSG.INVALID_COIN)
        return CHOOSING_COIN

    context.user_data["coin"] = coin
    context.user_data["output_coin"] = output_coin
    context.user_data["coin_key"] = coin_key

    info = COIN_INFO[coin_key]
    address = DEPOSIT_ADDRESSES[coin]

    keyboard = [[KeyboardButton(MSG.BTN_I_SENT)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        MSG.deposit_address(address, info['name'], output_coin, info['network'], info['confs']),
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    return WAITING_TXID


async def waiting_for_txid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle TXID input."""
    text = update.message.text
    MSG = get_user_msg(update)

    # Check for "I sent" button in any language
    if any(x in text.lower() for x in ["sent", "otpravil", "ugharkel"]):
        await update.message.reply_text(
            MSG.TXID_REQUEST,
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
                MSG.TXID_ALREADY_USED,
                parse_mode="HTML"
            )
            return WAITING_TXID

        context.user_data["txid"] = clean_text
        output_coin = context.user_data.get("output_coin", "USDT")

        network = "TRC20" if output_coin in ["USDT", "TRX"] else "Tron"

        await update.message.reply_text(
            MSG.txid_received(clean_text, output_coin, network),
            parse_mode="HTML"
        )
        return WAITING_ADDRESS
    else:
        await update.message.reply_text(
            MSG.INVALID_TXID,
            parse_mode="HTML"
        )
        return WAITING_TXID


async def address_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle address input."""
    address = update.message.text.strip()
    user_id = update.message.from_user.id
    MSG = get_user_msg(update)

    if not (address.startswith("T") and len(address) == 34):
        await update.message.reply_text(
            MSG.INVALID_ADDRESS,
            parse_mode="HTML"
        )
        return WAITING_ADDRESS

    coin = context.user_data.get("coin")
    txid = context.user_data.get("txid")

    if not coin or not txid:
        await update.message.reply_text(MSG.SESSION_EXPIRED)
        context.user_data.clear()
        return ConversationHandler.END

    # Check if TXID already used
    if await txid_exists(txid):
        owner_id = await get_txid_owner(txid)
        if owner_id == user_id:
            await update.message.reply_text(MSG.TXID_ALREADY_USED_BY_YOU)
        else:
            await update.message.reply_text(MSG.TXID_ALREADY_USED_BY_OTHER)
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

    keyboard = [[KeyboardButton(MSG.BTN_START), KeyboardButton(MSG.BTN_CHECK_STATUS)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        MSG.address_saved(address, txid, info['name'], output_coin, info['confs']),
        parse_mode="HTML",
        reply_markup=reply_markup
    )

    context.user_data.clear()
    return ConversationHandler.END


async def check_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check user's transaction status."""
    user_id = update.effective_user.id
    MSG = get_user_msg(update)

    async with aiosqlite.connect("swapbot.db") as conn:
        async with conn.execute(
            "SELECT txid, coin, status, confs, required_confs, onchain_amount, output_coin FROM deposits WHERE user_id = ? ORDER BY inserted_at DESC LIMIT 5",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        await update.message.reply_text(MSG.NO_TRANSACTIONS)
        return ConversationHandler.END

    # Status mapping
    status_map = {
        'NEW': MSG.STATUS_NEW,
        'CONFIRMING': MSG.STATUS_CONFIRMING,
        'CONFIRMED': MSG.STATUS_CONFIRMED,
        'SOLD': MSG.STATUS_SOLD,
        'WITHDRAWN': MSG.STATUS_WITHDRAWN,
        'TRADE_FAILED': MSG.STATUS_FAILED,
        'PROCESSING_ERROR': MSG.STATUS_ERROR,
    }

    message = MSG.transaction_history_header()

    for row in rows:
        status_text = status_map.get(row[2], row[2])
        message += MSG.transaction_item(
            row[1],
            row[6] or 'USDT',
            status_text,
            row[3],
            row[4],
            row[5]
        )

    await update.message.reply_text(message)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel conversation."""
    MSG = get_user_msg(update)
    context.user_data.clear()
    await update.message.reply_text(
        MSG.CANCELLED,
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown commands or messages."""
    MSG = get_user_msg(update)
    await update.message.reply_text(MSG.UNKNOWN_COMMAND)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the bot."""
    logger.error(f"Exception while handling update: {context.error}")
    try:
        if update and update.effective_message:
            MSG = get_user_msg(update)
            await update.effective_message.reply_text(MSG.BOT_ERROR)
    except Exception as e:
        logger.error(f"Error in error handler: {e}")


async def timeout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle conversation timeout."""
    if update and update.effective_message:
        MSG = get_user_msg(update)
        await update.effective_message.reply_text(MSG.SESSION_TIMEOUT)
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
        filters.Regex("(?i)check|status|prover|stugel") & ~filters.COMMAND,
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
    print(f"Fee: {fee_display()}")
    print("Languages: Armenian (hy), English (en), Russian (ru)")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
