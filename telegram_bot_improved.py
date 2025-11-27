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
        [KeyboardButton("📊 Ստուգել գործարքը")],
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
    
    # Check if user clicked "Check transaction"
    if "📊 Ստուգել" in text or "Ստուգել գործարքը" in text:
        await check_transaction(update, context)
        return ConversationHandler.END
    
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
    elif "Ստուգել" in text or "📊" in text:
        return await check_transaction(update, context)
    elif "/start" in text or "Նոր փոխանակում" in text:
        await start(update, context)
        return ConversationHandler.END
    
    if not coin:
        await update.message.reply_text("Խնդրում ենք ընտրել վերևի կոճակներից:")
        return CHOOSING_COIN
    elif "Ստուգել գործարքը" in text or "📊" in text:
        return await check_transaction(update, context)
    
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
        async with aiosqlite.connect("swapbot.db") as conn:
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
    
    keyboard = [[KeyboardButton("🔄 Նոր փոխանակում /start"), KeyboardButton("📊 Ստուգել")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
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
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END

async def check_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check user's transaction status"""
    user_id = update.effective_user.id
    
    async with aiosqlite.connect("swapbot.db") as conn:
        async with conn.execute(
            "SELECT txid, coin, status, confs, required_confs, amount, output_coin FROM deposits WHERE user_id = ? ORDER BY inserted_at DESC LIMIT 5",
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
    
    status_emoji = {
        "NEW": "🆕",
        "CONFIRMING": "⏳",
        "CONFIRMED": "✅",
        "SOLD": "💱",
        "WITHDRAWN": "🎉",
        "FAILED": "❌"
    }
    
    status_text = {
        "NEW": "Նոր",
        "CONFIRMING": "Հաստատվում է",
        "CONFIRMED": "Հաստատված",
        "SOLD": "Վաճառված",
        "WITHDRAWN": "Ավարտված",
        "FAILED": "Սխալ"
    }
    
    keyboard = [[KeyboardButton("🔄 /start")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"📊 Գործարքի կարգավիճակ\n\n"
        f"TXID: <code>{txid[:16]}...{txid[-8:]}</code>\n"
        f"Մետաղադրամ: {coin}\n"
        f"Կարգավիճակ: {status_emoji.get(status, '❓')} {status_text.get(status, status)}\n"
        f"Հաստատումներ: {confs}/{required}\n\n"
        f"{'✅ Շուտով կավարտվի!' if status in ['CONFIRMED', 'SOLD'] else '⏳ Սպասեք...' if status == 'CONFIRMING' else '🔍 Ստուգվում է...'}",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    
    return CHOOSING_COIN

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Չեղարկված է։ /start",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown commands or messages"""
    await update.message.reply_text(
        "❌ Սխալ հրաման\n\n"
        "Եթե չգիտեք ինչպես օգտագործել Conod բոտը,\n"
        "կարող եք գրել մեր օպերատորին՝\n\n"
        "📞 @Conodoperatorbot\n\n"
        "Կամ սեղմեք /start նոր փոխանակման համար։"
    )

def main():
    application = Application.builder().token(settings.telegram_bot_token).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_COIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, coin_chosen)],
            WAITING_TXID: [MessageHandler(filters.TEXT & ~filters.COMMAND, waiting_for_txid)],
            WAITING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, address_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)

    # Handler for check button (outside conversation)
    async def check_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await check_transaction(update, context)
    
    application.add_handler(MessageHandler(
        filters.Regex("📊.*Ստուգել") & ~filters.COMMAND,
        check_button_handler
    ))

    

    print("🤖 Bot starting...")
    print("📍 Supported swaps:")
    print("   • Bitcoin → USDT")
    print("   • Litecoin → USDT")
    print("   • Bitcoin → USDT")
    print("   • Litecoin → USDT")
    print("   • Dash → USDT")
    print("   • Dash → TRON")
    print("   • USDT → TRON")
    application.run_polling()

if __name__ == "__main__":
    main()
