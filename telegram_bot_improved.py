"""Telegram Bot with Dash to TRON support."""
import asyncio
import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, BotCommand
from app.db import txid_exists, get_txid_owner, get_db_path
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from app.config import settings
from libs.explorer_client import explorer_client
from app.models import CoinType
import aiosqlite
import re

logging.basicConfig(level=logging.INFO)

CHOOSING_COIN, WAITING_TXID, WAITING_ADDRESS = range(3)

# Get deposit addresses from config (centralized, not hardcoded)
def get_deposit_addresses():
    """Get deposit addresses from config - ensures consistency with worker"""
    return {
        "BTC": settings.addr_btc,
        "LTC": settings.addr_ltc,
        "DASH": settings.addr_dash,
        "XMR": settings.addr_xmr,
        "USDT": "TFqUpY6Xnk6QLaHxBr5hTnuHLfAPgLMLQF",  # USDT is always TRC20
    }

# Lazy-loaded to allow settings to initialize
DEPOSIT_ADDRESSES = None

def get_address(coin: str) -> str:
    """Get deposit address for a coin"""
    global DEPOSIT_ADDRESSES
    if DEPOSIT_ADDRESSES is None:
        DEPOSIT_ADDRESSES = get_deposit_addresses()
    return DEPOSIT_ADDRESSES.get(coin, "")

COIN_INFO = {
    "BTC": {"name": "Bitcoin", "network": "Bitcoin", "confs": 2, "to": "USDT"},
    "LTC": {"name": "Litecoin", "network": "Litecoin", "confs": 4, "to": "USDT"},
    "DASH": {"name": "Dash", "network": "Dash", "confs": 12, "to": "USDT"},
    "DASH_TRX": {"name": "Dash", "network": "Dash", "confs": 12, "to": "TRX"},
    "XMR": {"name": "Monero", "network": "Monero", "confs": 10, "to": "USDT"},
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("₿ Bitcoin → USDT"), KeyboardButton("Ł Litecoin → USDT")],
        [KeyboardButton("💎 Dash → USDT"), KeyboardButton("💎 Dash → TRON")],
        [KeyboardButton("🔒 Monero → USDT")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "👋 Բարև: Ուրախ եմ աշխատել քեզ համար։\n"
        "\n⚠️ Նվազագույն գումար: $20 USD\n"
        "💡 Միջնորդավճար: 3% + $1\n"
        "✌️ Ընտրեք փոխանակման տեսակը:",
        reply_markup=reply_markup
    )
    return CHOOSING_COIN

async def coin_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    
    coin = None
    output_coin = "USDT"
    coin_key = None
    
    if "Bitcoin" in text and "USDT" in text:
        coin = "BTC"
        output_coin = "USDT"
        coin_key = "BTC"
    elif "Litecoin" in text and "USDT" in text:
        coin = "LTC"
        output_coin = "USDT"
        coin_key = "LTC"
    elif "Dash" in text and "USDT" in text:
        coin = "DASH"
        output_coin = "USDT"
        coin_key = "DASH"
    elif "Dash" in text and "TRON" in text:
        coin = "DASH"
        output_coin = "TRX"
        coin_key = "DASH_TRX"
    elif "Monero" in text and "USDT" in text:
        coin = "XMR"
        output_coin = "USDT"
        coin_key = "XMR"
    
    if not coin:
        await update.message.reply_text("Խնդրում ենք ընտրել վերևի կոճակներից:")
        return CHOOSING_COIN
    
    context.user_data["coin"] = coin
    context.user_data["output_coin"] = output_coin
    context.user_data["coin_key"] = coin_key
    
    info = COIN_INFO[coin_key]
    address = get_address(coin)
    
    keyboard = [[KeyboardButton("Ես ուղարկել եմ ✅")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        f"Ձեր վճարման հասցեն:\n\n"
        f"<code>{address}</code>\n\n"
        f"💱 Դուք ընտրեցիք {info['name']} → {output_coin}\n"
        f"🌐 Ցանց: {info['network']}\n"
        f"✅ Հաստատումներ: {info['confs']}\n"
        f"💰 Գանձարկվում է 3% միջնորդավճար\n"
        f"⏱ Միջին տևողություն: 20–30 րոպե\n\n"
        f"Ուղարկելուց հետո սեղմեք «Ես ուղարկել եմ» կոճակը։",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    return WAITING_TXID

async def waiting_for_txid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if "Ես ուղարկել եմ" in text:
        await update.message.reply_text(
            "Ստացվեց ✅\n\n"
            "Խնդրում ենք ուղարկել գործարքի HASH-ը (64 նիշ):\n\n"
            "Օրինակ:\n"
            "<code>a65b33369cf0bcd1b4e7a47f00e6536612210aeb0ddb4e6ac557c9f83d316545</code>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
        return WAITING_TXID
    
    clean_text = text.strip().lower()
    if re.match(r"^[a-f0-9]{64}$", clean_text):
        # Check if TXID already exists
        import aiosqlite
        async with aiosqlite.connect(get_db_path()) as conn:
            async with conn.execute("SELECT txid FROM deposits WHERE txid = ?", (clean_text,)) as cursor:
                existing = await cursor.fetchone()
        
        if existing:
            await update.message.reply_text(
                "❌ Այս գործարքը արդեն օգտագործվել է։\n\n"
                "Խնդրում ենք ուղարկել ՆՈՐ գործարքի HASH:\n\n"
                "Օրինակ:\n"
                "<code>6559ce2924b306bde3ca6433b92e9bac94821f587fda74ada758fd8477cf4f16</code>",
                parse_mode="HTML"
            )
            return WAITING_TXID
        
        context.user_data["txid"] = clean_text
        output_coin = context.user_data.get("output_coin", "USDT")
        
        network = "TRC20" if output_coin in ["USDT", "TRX"] else "Tron"
        
        await update.message.reply_text(
            f"TXID ստացվել է ✅\n\n"
            f"<code>{clean_text[:32]}\n{clean_text[32:]}</code>\n\n"
            f"Հիմա խնդրում ենք ուղարկել ձեր {output_coin} ({network}) ստացման հասցեն:\n\n"
            f"Օրինակ:\n"
            f"<code>TVQXrLPpULB6y4KnJMyZorxWQqR7UhhL3g</code>",
            parse_mode="HTML"
        )
        return WAITING_ADDRESS
    else:
        await update.message.reply_text(
            "❌ Սխալ ձևաչափ։\n\n"
            "TXID-ն պետք է լինի 64 նիշ (0-9, a-f)։",
            parse_mode="HTML"
        )
        return WAITING_TXID

async def address_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text.strip()
    user_id = update.message.from_user.id
    
    if not (address.startswith("T") and len(address) == 34):
        await update.message.reply_text(
            "❌ Սխալ հասցե։\n\n"
            "TRC20 հասցեն պետք է սկսվի T տառով և լինի 34 նիշ։",
            parse_mode="HTML"
        )
        return WAITING_ADDRESS
    
    coin = context.user_data.get("coin")
    txid = context.user_data.get("txid")
    
    # Check if TXID already used
    if await txid_exists(txid):
        owner_id = await get_txid_owner(txid)
        if owner_id == user_id:
            await update.message.reply_text(
                "⚠️ Այս գործարքը արդեն օգտագործվել է։\nԽնդրում ենք ուղարկել ՆՈՐ գործարք"
            )
        else:
            await update.message.reply_text(
                "❌ Այս գործարքն արդեն օգտագործված է այլ օգտատիրոջ կողմից"
            )
        context.user_data.clear()
        return ConversationHandler.END
    output_coin = context.user_data.get("output_coin", "USDT")
    coin_key = context.user_data.get("coin_key")
    
    async with aiosqlite.connect(get_db_path()) as conn:
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
    
    
    await update.message.reply_text(
        f"✅ Պահպանվեց {output_coin} հասցեն:\n"
        f"<code>{address}</code>\n\n"
        f"🔎 Սկսում ենք ստուգել ձեր փոխանցումը։\n\n"
        f"📊 Գործարքի տվյալներ:\n"
        f"• TXID: <code>{txid[:16]}...{txid[-8:]}</code>\n"
        f"• {info['name']} → {output_coin}\n"
        f"• Հաստատումներ: 0/{info['confs']}\n\n"
        f"⏳ Խնդրում ենք սպասել...\n"
        f"📱 Դուք կստանաք ծանուցումներ այստեղ:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

async def check_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check user's transaction status"""
    user_id = update.effective_user.id
    
    async with aiosqlite.connect(get_db_path()) as conn:
        async with conn.execute(
            "SELECT txid, coin, status, confs, required_confs, onchain_amount, output_coin FROM deposits WHERE user_id = ? ORDER BY inserted_at DESC LIMIT 5",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
    
    if not rows:
        await update.message.reply_text(
            "❌ Դուք դեռ գործարք չունեք։\n"
            "Սկսելու համար սեղմեք /start"
        )
        return
    
    message = "📊 Ձեր վերջին գործարքները:\n\n"
    
    for row in rows:
        status_emoji = {
            'NEW': '🆕',
            'CONFIRMING': '⏳',
            'CONFIRMED': '✅',
            'WITHDRAWN': '🎉',
            'TRADE_FAILED': '❌',
        }.get(row[2], '❓')
        
        message += f"{status_emoji} {row[1]} → {row[6] or 'USDT'}\n"
        message += f"   Status: {row[2]}\n"
        message += f"   Confs: {row[3]}/{row[4]}\n"
        if row[5]:
            message += f"   Amount: {row[5]:.4f}\n"
        message += "\n"
    
    await update.message.reply_text(message)
    return

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Չեղարկված է։ /start",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END




async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message with all commands"""
    await update.message.reply_text(
        "📚 Help:\n\n"
        "💱 Available exchanges:\n"
        "• ₿ Bitcoin → USDT\n"
        "• Ł Litecoin → USDT\n"
        "• 💎 Dash → USDT\n"
        "• 💎 Dash → TRON\n"
        "• 🔒 Monero → USDT\n\n"
        "📋 Commands:\n"
        "/start    – Start new exchange\n"
        "/status   – Check transaction status\n"
        "/check    – Same as /status\n"
        "/cancel   – Cancel current operation\n"
        "/operator – Contact support\n"
        "/help     – Show this message\n\n"
        "⚠️ Minimum: $20 USD\n"
        "💰 Fee: 3% + $1"
    )


async def operator_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Contact support operator"""
    await update.message.reply_text(
        "📞 Contact Support:\n\n"
        "For assistance, contact:\n"
        "@Conodoperatorbot\n\n"
        "We respond within 24 hours."
    )

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown commands - show help"""
    await update.message.reply_text(
        "❓ Unknown command.\n\n"
        "Available commands:\n"
        "/start – Start new exchange\n"
        "/status – Check transaction status\n"
        "/help – Show all commands\n\n"
        "📞 Support: @Conodoperatorbot"
    )

async def set_bot_commands(application):
    """Set bot commands menu automatically"""
    commands = [
        BotCommand("start", "Start new exchange"),
        BotCommand("status", "Check transaction status"),
        BotCommand("check", "Same as /status"),
        BotCommand("cancel", "Cancel current operation"),
        BotCommand("help", "Show all commands"),
        BotCommand("operator", "Contact support"),
    ]
    await application.bot.set_my_commands(commands)
    print("✅ Bot commands menu set successfully!")


def main():
    application = Application.builder().token(settings.telegram_bot_token).post_init(set_bot_commands).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_COIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, coin_chosen)],
            WAITING_TXID: [MessageHandler(filters.TEXT & ~filters.COMMAND, waiting_for_txid)],
            WAITING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, address_received)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("status", check_transaction),
            CommandHandler("check", check_transaction),
            CommandHandler("help", help_command),
            CommandHandler("operator", operator_command),
            CommandHandler("start", start),
        ],
    )
    
    application.add_handler(conv_handler)

    # Additional command handlers
    application.add_handler(CommandHandler("status", check_transaction))
    application.add_handler(CommandHandler("check", check_transaction))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("operator", operator_command))
    
    # Handle unknown messages (outside conversation)
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    print("🤖 Bot starting...")
    print("📍 Supported swaps:")
    print("   • Bitcoin → USDT")
    print("   • Litecoin → USDT")
    print("   • Dash → USDT")
    print("   • Dash → TRON")
    print("   • Monero → USDT")
    application.run_polling()

if __name__ == "__main__":
    main()
