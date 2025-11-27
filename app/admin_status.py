"""
Admin Status Module for Convertbot
Provides essential bot status metrics
"""
import asyncio
import aiosqlite
from datetime import datetime, timedelta
from typing import Dict, Any
from app.config import settings
from app.logger import setup_logger

logger = setup_logger(__name__)

# Track worker heartbeat
_last_worker_run: datetime = None
_worker_queue_size: int = 0


def update_worker_heartbeat():
    """Called by worker after each successful cycle"""
    global _last_worker_run
    _last_worker_run = datetime.now()


def update_queue_size(size: int):
    """Called by worker to update queue size"""
    global _worker_queue_size
    _worker_queue_size = size


async def get_bot_status() -> Dict[str, Any]:
    """
    Get comprehensive bot status for admin command.

    Returns dict with:
    - orders_today: Orders created in last 24h
    - orders_total: All-time orders
    - orders_open: Currently open/unresolved orders
    - users_today: Active users in last 24h
    - users_total: Total registered users
    - queue_size: Worker queue size
    - last_worker_run: Seconds since last worker cycle
    - mode: DRY_RUN or PRODUCTION
    - failed_today: Failed orders in last 24h
    """
    db_path = settings.database_url.replace("sqlite:///", "")

    stats = {
        "orders_today": 0,
        "orders_total": 0,
        "orders_open": 0,
        "users_today": 0,
        "users_total": 0,
        "queue_size": _worker_queue_size,
        "last_worker_run": None,
        "mode": "DRY_RUN" if settings.dry_run else "PRODUCTION",
        "failed_today": 0,
        "volume_today_usd": 0.0,
    }

    try:
        async with aiosqlite.connect(db_path) as conn:
            # Orders today
            cursor = await conn.execute("""
                SELECT COUNT(*) FROM deposits
                WHERE inserted_at > datetime('now', '-24 hours')
            """)
            row = await cursor.fetchone()
            stats["orders_today"] = row[0] if row else 0

            # Orders total
            cursor = await conn.execute("SELECT COUNT(*) FROM deposits")
            row = await cursor.fetchone()
            stats["orders_total"] = row[0] if row else 0

            # Open orders (NEW, CONFIRMING, CONFIRMED, SOLD)
            cursor = await conn.execute("""
                SELECT COUNT(*) FROM deposits
                WHERE status IN ('NEW', 'CONFIRMING', 'CONFIRMED', 'SOLD')
            """)
            row = await cursor.fetchone()
            stats["orders_open"] = row[0] if row else 0

            # Active users today
            cursor = await conn.execute("""
                SELECT COUNT(DISTINCT user_id) FROM deposits
                WHERE inserted_at > datetime('now', '-24 hours')
            """)
            row = await cursor.fetchone()
            stats["users_today"] = row[0] if row else 0

            # Total users
            cursor = await conn.execute("SELECT COUNT(*) FROM users")
            row = await cursor.fetchone()
            stats["users_total"] = row[0] if row else 0

            # Failed today
            cursor = await conn.execute("""
                SELECT COUNT(*) FROM deposits
                WHERE status = 'TRADE_FAILED'
                AND inserted_at > datetime('now', '-24 hours')
            """)
            row = await cursor.fetchone()
            stats["failed_today"] = row[0] if row else 0

            # Volume today (completed withdrawals)
            cursor = await conn.execute("""
                SELECT COALESCE(SUM(onchain_amount), 0) FROM deposits
                WHERE status = 'WITHDRAWN'
                AND inserted_at > datetime('now', '-24 hours')
            """)
            row = await cursor.fetchone()
            stats["volume_today_usd"] = row[0] if row else 0.0

    except Exception as e:
        logger.error(f"Error getting bot status: {e}")

    # Worker heartbeat
    if _last_worker_run:
        delta = datetime.now() - _last_worker_run
        stats["last_worker_run"] = int(delta.total_seconds())
    else:
        stats["last_worker_run"] = -1  # Never run

    return stats


def format_status_message(stats: Dict[str, Any]) -> str:
    """Format status dict as Telegram message"""
    # Format last worker run
    if stats["last_worker_run"] == -1:
        worker_status = "❌ Never"
    elif stats["last_worker_run"] > 120:
        worker_status = f"⚠️ {stats['last_worker_run']}s ago"
    else:
        worker_status = f"✅ {stats['last_worker_run']}s ago"

    # Mode indicator
    mode_emoji = "🔴" if stats["mode"] == "PRODUCTION" else "🟡"

    message = f"""📊 Bot Status

🧾 Orders:
• Today: {stats['orders_today']}
• All-time: {stats['orders_total']:,}
• Open now: {stats['orders_open']}
• Failed today: {stats['failed_today']}

👥 Users:
• Active today: {stats['users_today']}
• Total users: {stats['users_total']:,}

💰 Volume:
• Today: ${stats['volume_today_usd']:.2f}

⚙️ System:
• Queue size: {stats['queue_size']}
• Last worker run: {worker_status}
• Mode: {mode_emoji} {stats['mode']}"""

    return message


async def get_detailed_status() -> Dict[str, Any]:
    """Get more detailed status for debugging"""
    basic = await get_bot_status()
    db_path = settings.database_url.replace("sqlite:///", "")

    try:
        async with aiosqlite.connect(db_path) as conn:
            # Status breakdown
            cursor = await conn.execute("""
                SELECT status, COUNT(*) as count
                FROM deposits
                GROUP BY status
            """)
            rows = await cursor.fetchall()
            basic["status_breakdown"] = {row[0]: row[1] for row in rows}

            # Coin breakdown (last 24h)
            cursor = await conn.execute("""
                SELECT coin, COUNT(*) as count
                FROM deposits
                WHERE inserted_at > datetime('now', '-24 hours')
                GROUP BY coin
            """)
            rows = await cursor.fetchall()
            basic["coin_breakdown"] = {row[0]: row[1] for row in rows}

            # Recent errors
            cursor = await conn.execute("""
                SELECT txid, coin, status, inserted_at
                FROM deposits
                WHERE status IN ('TRADE_FAILED', 'PROCESSING_ERROR')
                ORDER BY inserted_at DESC
                LIMIT 5
            """)
            rows = await cursor.fetchall()
            basic["recent_errors"] = [
                {"txid": r[0][:16], "coin": r[1], "status": r[2], "time": r[3]}
                for r in rows
            ]

    except Exception as e:
        logger.error(f"Error getting detailed status: {e}")

    return basic


# ==================== Admin Commands Integration ====================

async def handle_status_command(user_id: int) -> str:
    """Handle /status admin command"""
    # Check if user is admin
    if str(user_id) != str(settings.admin_chat_id):
        return "❌ Unauthorized. Admin only command."

    stats = await get_bot_status()
    return format_status_message(stats)


async def handle_detailed_status_command(user_id: int) -> str:
    """Handle /status_detailed admin command"""
    if str(user_id) != str(settings.admin_chat_id):
        return "❌ Unauthorized. Admin only command."

    stats = await get_detailed_status()
    basic_msg = format_status_message(stats)

    # Add detailed info
    extra = "\n\n📈 Breakdown:"

    if stats.get("status_breakdown"):
        extra += "\n• Status: " + ", ".join(
            f"{k}:{v}" for k, v in stats["status_breakdown"].items()
        )

    if stats.get("coin_breakdown"):
        extra += "\n• Coins (24h): " + ", ".join(
            f"{k}:{v}" for k, v in stats["coin_breakdown"].items()
        )

    if stats.get("recent_errors"):
        extra += "\n\n❌ Recent Errors:"
        for err in stats["recent_errors"]:
            extra += f"\n• {err['coin']} {err['txid']}... ({err['status']})"

    return basic_msg + extra
