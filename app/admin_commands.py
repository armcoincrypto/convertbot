"""
Admin Commands for Convertbot
Telegram bot commands for operators
"""
import asyncio
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes
from app.config import settings
from app.logger import setup_logger
from app.admin_status import get_bot_status, format_status_message, get_detailed_status

logger = setup_logger(__name__)


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    admin_ids = str(settings.admin_chat_id).split(",")
    return str(user_id) in admin_ids


# ==================== Status Commands ====================

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /status - Show bot status dashboard

    📊 Bot Status
    🧾 Orders: Today, All-time, Open
    👥 Users: Active, Total
    ⚙️ System: Queue, Worker, Mode
    """
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized")
        return

    stats = await get_bot_status()
    message = format_status_message(stats)
    await update.message.reply_text(message)


async def cmd_status_detailed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /status_detailed - Show detailed status with breakdowns
    """
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized")
        return

    from app.admin_status import handle_detailed_status_command
    message = await handle_detailed_status_command(update.effective_user.id)
    await update.message.reply_text(message)


# ==================== Transaction Commands ====================

async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /pending - List all pending transactions
    """
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized")
        return

    db_path = settings.database_url.replace("sqlite:///", "")

    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("""
            SELECT txid, coin, user_id, status, confs, required_confs,
                   onchain_amount, inserted_at
            FROM deposits
            WHERE status IN ('NEW', 'CONFIRMING', 'CONFIRMED', 'SOLD')
            ORDER BY inserted_at DESC
            LIMIT 20
        """)
        rows = await cursor.fetchall()

    if not rows:
        await update.message.reply_text("✅ No pending transactions")
        return

    message = "📋 Pending Transactions\n\n"
    for row in rows:
        txid, coin, user_id, status, confs, req_confs, amount, inserted = row
        age = ""
        try:
            dt = datetime.fromisoformat(inserted)
            mins = (datetime.now() - dt).total_seconds() / 60
            age = f"{int(mins)}m" if mins < 60 else f"{int(mins/60)}h"
        except:
            pass

        status_emoji = {"NEW": "🆕", "CONFIRMING": "⏳", "CONFIRMED": "✅", "SOLD": "💱"}.get(status, "❓")

        message += f"{status_emoji} {coin} | {status}\n"
        message += f"   TXID: {txid[:12]}...\n"
        message += f"   User: {user_id} | Confs: {confs}/{req_confs}\n"
        if amount:
            message += f"   Amount: {amount:.6f}\n"
        message += f"   Age: {age}\n\n"

    await update.message.reply_text(message)


async def cmd_tx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /tx <txid> - Get details for specific transaction
    """
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized")
        return

    if not context.args:
        await update.message.reply_text("Usage: /tx <txid>")
        return

    txid_query = context.args[0].lower()
    db_path = settings.database_url.replace("sqlite:///", "")

    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("""
            SELECT * FROM deposits WHERE txid LIKE ?
        """, (f"%{txid_query}%",))
        row = await cursor.fetchone()

        if not row:
            await update.message.reply_text(f"❌ Transaction not found: {txid_query}")
            return

        # Get column names
        columns = [desc[0] for desc in cursor.description]
        data = dict(zip(columns, row))

    message = f"📄 Transaction Details\n\n"
    message += f"TXID: <code>{data.get('txid', 'N/A')}</code>\n"
    message += f"Coin: {data.get('coin', 'N/A')}\n"
    message += f"Status: {data.get('status', 'N/A')}\n"
    message += f"User ID: {data.get('user_id', 'N/A')}\n"
    message += f"Amount: {data.get('onchain_amount', 'N/A')}\n"
    message += f"Confs: {data.get('confs', 0)}/{data.get('required_confs', 'N/A')}\n"
    message += f"Target: {data.get('target_address', 'N/A')}\n"
    message += f"Output: {data.get('output_coin', 'USDT')}\n"
    message += f"Created: {data.get('inserted_at', 'N/A')}\n"

    await update.message.reply_text(message, parse_mode="HTML")


async def cmd_retry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /retry <txid> - Retry a failed transaction
    """
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized")
        return

    if not context.args:
        await update.message.reply_text("Usage: /retry <txid>")
        return

    txid = context.args[0].lower()
    db_path = settings.database_url.replace("sqlite:///", "")

    async with aiosqlite.connect(db_path) as conn:
        # Check current status
        cursor = await conn.execute(
            "SELECT status FROM deposits WHERE txid = ?", (txid,)
        )
        row = await cursor.fetchone()

        if not row:
            await update.message.reply_text(f"❌ Transaction not found")
            return

        current_status = row[0]

        if current_status == "WITHDRAWN":
            await update.message.reply_text("⚠️ Transaction already completed")
            return

        # Reset to CONFIRMED for retry
        await conn.execute(
            "UPDATE deposits SET status = 'CONFIRMED' WHERE txid = ?",
            (txid,)
        )
        await conn.commit()

    logger.info(f"Admin retry: {txid[:16]}... (was {current_status})")
    await update.message.reply_text(f"✅ Transaction reset to CONFIRMED\nPrevious status: {current_status}")


# ==================== User Commands ====================

async def cmd_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /user <user_id> - Get user details and history
    """
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized")
        return

    if not context.args:
        await update.message.reply_text("Usage: /user <user_id>")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID")
        return

    db_path = settings.database_url.replace("sqlite:///", "")

    async with aiosqlite.connect(db_path) as conn:
        # Get user info
        cursor = await conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        )
        user = await cursor.fetchone()

        # Get transaction history
        cursor = await conn.execute("""
            SELECT coin, status, onchain_amount, inserted_at
            FROM deposits
            WHERE user_id = ?
            ORDER BY inserted_at DESC
            LIMIT 10
        """, (user_id,))
        txs = await cursor.fetchall()

        # Get stats
        cursor = await conn.execute("""
            SELECT COUNT(*), COALESCE(SUM(onchain_amount), 0)
            FROM deposits
            WHERE user_id = ? AND status = 'WITHDRAWN'
        """, (user_id,))
        stats = await cursor.fetchone()

    message = f"👤 User: {user_id}\n\n"

    if user:
        message += f"Address: {user[1] if len(user) > 1 else 'N/A'}\n"

    message += f"Completed swaps: {stats[0] if stats else 0}\n"
    message += f"Total volume: {stats[1]:.4f if stats else 0}\n\n"

    if txs:
        message += "Recent transactions:\n"
        for tx in txs:
            coin, status, amount, date = tx
            message += f"• {coin} | {status} | {amount or 'N/A'}\n"

    await update.message.reply_text(message)


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /broadcast <message> - Send message to all active users
    """
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized")
        return

    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    message = " ".join(context.args)
    db_path = settings.database_url.replace("sqlite:///", "")

    # Get active users (had transaction in last 7 days)
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("""
            SELECT DISTINCT user_id FROM deposits
            WHERE inserted_at > datetime('now', '-7 days')
        """)
        users = await cursor.fetchall()

    from libs.telegram_client import TelegramClient
    telegram = TelegramClient(settings.telegram_bot_token, settings.admin_chat_id)

    sent = 0
    failed = 0

    for (user_id,) in users:
        try:
            await telegram.send_message(user_id, f"📢 {message}")
            sent += 1
            await asyncio.sleep(0.1)  # Rate limit
        except Exception:
            failed += 1

    await update.message.reply_text(f"✅ Broadcast complete\nSent: {sent}\nFailed: {failed}")


# ==================== System Commands ====================

async def cmd_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /mode - Show current mode (DRY_RUN/PRODUCTION)
    """
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized")
        return

    mode = "DRY_RUN 🟡" if settings.dry_run else "PRODUCTION 🔴"
    await update.message.reply_text(f"Current mode: {mode}")


async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /logs [n] - Show last n log entries (default 10)
    """
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized")
        return

    n = 10
    if context.args:
        try:
            n = min(int(context.args[0]), 50)
        except ValueError:
            pass

    log_file = "/var/log/convertbot/worker.log"
    if not os.path.exists(log_file):
        log_file = "logs/worker.log"

    try:
        import os
        with open(log_file, 'r') as f:
            lines = f.readlines()[-n:]

        message = f"📜 Last {n} log entries:\n\n"
        for line in lines:
            # Truncate long lines
            if len(line) > 100:
                line = line[:100] + "..."
            message += f"{line}"

        # Split if too long
        if len(message) > 4000:
            message = message[:4000] + "\n..."

        await update.message.reply_text(message)
    except Exception as e:
        await update.message.reply_text(f"❌ Could not read logs: {e}")


async def cmd_help_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /admin - Show admin commands help
    """
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized")
        return

    help_text = """🔧 Admin Commands

📊 Status:
/status - Bot dashboard
/status_detailed - Detailed stats
/mode - Current mode

📋 Transactions:
/pending - List pending txs
/tx <txid> - Transaction details
/retry <txid> - Retry failed tx

👥 Users:
/user <id> - User details
/broadcast <msg> - Message users

⚙️ System:
/logs [n] - View logs
/admin - This help"""

    await update.message.reply_text(help_text)


# ==================== Register Commands ====================

def register_admin_commands(application):
    """Register all admin command handlers"""
    from telegram.ext import CommandHandler

    commands = [
        ("status", cmd_status),
        ("status_detailed", cmd_status_detailed),
        ("pending", cmd_pending),
        ("tx", cmd_tx),
        ("retry", cmd_retry),
        ("user", cmd_user),
        ("broadcast", cmd_broadcast),
        ("mode", cmd_mode),
        ("logs", cmd_logs),
        ("admin", cmd_help_admin),
    ]

    for cmd_name, handler in commands:
        application.add_handler(CommandHandler(cmd_name, handler))

    logger.info(f"Registered {len(commands)} admin commands")


# Fix missing import
import os
