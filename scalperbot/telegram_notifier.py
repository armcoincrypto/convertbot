"""
Telegram Notifier - Send trading alerts to Telegram
"""
import logging
import asyncio
from typing import Optional
import aiohttp

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Send notifications to Telegram"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

        if self.enabled:
            logger.info("📱 Telegram notifications enabled")
        else:
            logger.info("📱 Telegram notifications disabled (no credentials)")

    async def send_message(self, message: str, parse_mode: str = "HTML"):
        """Send a message to Telegram"""
        if not self.enabled:
            return

        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as response:
                    if response.status == 200:
                        logger.debug("✅ Telegram message sent")
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Telegram send failed: {error_text}")

        except asyncio.TimeoutError:
            logger.error("❌ Telegram timeout")
        except Exception as e:
            logger.error(f"❌ Telegram error: {e}")

    async def notify_trade_opened(self, symbol: str, side: str, entry_price: float,
                                   quantity: float, position_size_usd: float):
        """Notify when a trade is opened"""
        message = (
            f"🟢 <b>TRADE OPENED</b>\n\n"
            f"<b>{symbol}</b> {side.upper()}\n"
            f"Entry: ${entry_price:.4f}\n"
            f"Size: {quantity:.6f} (${position_size_usd:.2f})\n"
            f"Time: {self._get_time()}"
        )
        await self.send_message(message)

    async def notify_trade_closed(self, symbol: str, entry_price: float,
                                   exit_price: float, pnl_bps: float,
                                   pnl_usd: float, reason: str):
        """Notify when a trade is closed"""
        emoji = "🟢" if pnl_bps >= 0 else "🔴"
        message = (
            f"{emoji} <b>TRADE CLOSED</b>\n\n"
            f"<b>{symbol}</b>\n"
            f"Entry: ${entry_price:.4f}\n"
            f"Exit: ${exit_price:.4f}\n"
            f"PnL: {pnl_bps:+.1f} bps (${pnl_usd:+.2f})\n"
            f"Reason: {reason}\n"
            f"Time: {self._get_time()}"
        )
        await self.send_message(message)

    async def notify_daily_summary(self, total_trades: int, wins: int, losses: int,
                                    total_pnl_usd: float, total_pnl_pct: float):
        """Send daily performance summary"""
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        emoji = "📈" if total_pnl_usd >= 0 else "📉"

        message = (
            f"{emoji} <b>DAILY SUMMARY</b>\n\n"
            f"Trades: {total_trades} ({wins}W-{losses}L)\n"
            f"Win Rate: {win_rate:.1f}%\n"
            f"PnL: ${total_pnl_usd:+.2f} ({total_pnl_pct:+.2f}%)\n"
            f"Time: {self._get_time()}"
        )
        await self.send_message(message)

    async def notify_risk_breaker(self, daily_pnl_pct: float, limit_pct: float):
        """Notify when risk breaker is triggered"""
        message = (
            f"⛔ <b>RISK BREAKER TRIGGERED</b>\n\n"
            f"Daily Loss: {daily_pnl_pct:.2f}%\n"
            f"Limit: {limit_pct:.2f}%\n"
            f"<b>Trading stopped for today</b>\n"
            f"Time: {self._get_time()}"
        )
        await self.send_message(message)

    async def notify_error(self, error_type: str, details: str):
        """Notify on errors"""
        message = (
            f"⚠️ <b>ERROR: {error_type}</b>\n\n"
            f"{details}\n"
            f"Time: {self._get_time()}"
        )
        await self.send_message(message)

    async def notify_startup(self, mode: str, balance: float, pairs: list):
        """Notify when bot starts"""
        mode_emoji = "🔶" if mode == "DRY_RUN" else "🔴"
        message = (
            f"🚀 <b>ScalperBot Started</b>\n\n"
            f"Mode: {mode_emoji} {mode}\n"
            f"Balance: ${balance:.2f}\n"
            f"Pairs: {', '.join(pairs)}\n"
            f"Time: {self._get_time()}"
        )
        await self.send_message(message)

    async def notify_position_update(self, symbol: str, pnl_bps: float,
                                      time_held: int, highest_price: float):
        """Notify position update (optional, can be used for long-running positions)"""
        emoji = "📈" if pnl_bps >= 0 else "📉"
        message = (
            f"{emoji} <b>Position Update</b>\n\n"
            f"<b>{symbol}</b>\n"
            f"PnL: {pnl_bps:+.1f} bps\n"
            f"High: ${highest_price:.4f}\n"
            f"Time: {time_held}s\n"
        )
        await self.send_message(message)

    def _get_time(self):
        """Get current time string"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
