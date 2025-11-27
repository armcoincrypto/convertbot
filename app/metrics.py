"""
Prometheus Metrics for Convertbot
Exposes metrics for monitoring and alerting
"""
import time
import asyncio
from typing import Optional
from app.logger import setup_logger
from app.config import settings

logger = setup_logger(__name__)

# Try to import prometheus_client
try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server, REGISTRY
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed. Metrics disabled.")


class Metrics:
    """Prometheus metrics collector for Convertbot"""

    def __init__(self):
        self.enabled = settings.metrics_enabled and PROMETHEUS_AVAILABLE
        self._server_started = False

        if not self.enabled:
            logger.info("Metrics collection disabled")
            return

        # Transaction metrics
        self.deposits_total = Counter(
            'convertbot_deposits_total',
            'Total number of deposits',
            ['coin', 'status']
        )

        self.deposits_pending = Gauge(
            'convertbot_deposits_pending',
            'Number of pending deposits',
            ['coin']
        )

        self.deposits_confirmed = Counter(
            'convertbot_deposits_confirmed_total',
            'Total confirmed deposits',
            ['coin']
        )

        self.withdrawals_total = Counter(
            'convertbot_withdrawals_total',
            'Total withdrawals',
            ['coin', 'status']
        )

        self.withdrawals_failed = Counter(
            'convertbot_withdrawals_failed_total',
            'Failed withdrawals',
            ['coin', 'reason']
        )

        # Volume metrics
        self.volume_usd = Counter(
            'convertbot_volume_usd_total',
            'Total volume processed in USD',
            ['coin', 'direction']
        )

        # Processing time metrics
        self.processing_time = Histogram(
            'convertbot_processing_seconds',
            'Time to process deposits',
            ['coin', 'stage'],
            buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600]
        )

        # Worker metrics
        self.worker_cycles = Counter(
            'convertbot_worker_cycles_total',
            'Total worker cycles executed'
        )

        self.worker_errors = Counter(
            'convertbot_worker_errors_total',
            'Total worker errors',
            ['error_type']
        )

        self.worker_last_cycle = Gauge(
            'convertbot_worker_last_cycle_timestamp',
            'Timestamp of last worker cycle'
        )

        # Rate limiting metrics
        self.rate_limit_hits = Counter(
            'convertbot_rate_limit_hits_total',
            'Number of rate limit blocks',
            ['limit_type']
        )

        # Exchange metrics
        self.exchange_requests = Counter(
            'convertbot_exchange_requests_total',
            'Exchange API requests',
            ['endpoint', 'status']
        )

        self.exchange_latency = Histogram(
            'convertbot_exchange_latency_seconds',
            'Exchange API latency',
            ['endpoint'],
            buckets=[0.1, 0.25, 0.5, 1, 2.5, 5, 10]
        )

        # Blockchain metrics
        self.blockchain_requests = Counter(
            'convertbot_blockchain_requests_total',
            'Blockchain explorer requests',
            ['coin', 'status']
        )

        # User metrics
        self.active_users = Gauge(
            'convertbot_active_users',
            'Number of users with pending transactions'
        )

        self.new_users = Counter(
            'convertbot_new_users_total',
            'New user registrations'
        )

        # System metrics
        self.db_connections = Gauge(
            'convertbot_db_connections',
            'Active database connections'
        )

        self.uptime = Gauge(
            'convertbot_uptime_seconds',
            'Bot uptime in seconds'
        )

        self._start_time = time.time()

    def start_server(self, port: Optional[int] = None):
        """Start the Prometheus metrics HTTP server"""
        if not self.enabled or self._server_started:
            return

        port = port or settings.metrics_port

        try:
            start_http_server(port)
            self._server_started = True
            logger.info(f"✅ Metrics server started on port {port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")

    # ==================== Recording Methods ====================

    def record_deposit(self, coin: str, status: str):
        """Record a deposit event"""
        if self.enabled:
            self.deposits_total.labels(coin=coin, status=status).inc()

    def set_pending_deposits(self, coin: str, count: int):
        """Set pending deposits gauge"""
        if self.enabled:
            self.deposits_pending.labels(coin=coin).set(count)

    def record_confirmed(self, coin: str):
        """Record a confirmed deposit"""
        if self.enabled:
            self.deposits_confirmed.labels(coin=coin).inc()

    def record_withdrawal(self, coin: str, status: str):
        """Record a withdrawal event"""
        if self.enabled:
            self.withdrawals_total.labels(coin=coin, status=status).inc()

    def record_withdrawal_failed(self, coin: str, reason: str):
        """Record a failed withdrawal"""
        if self.enabled:
            self.withdrawals_failed.labels(coin=coin, reason=reason).inc()

    def record_volume(self, coin: str, direction: str, amount_usd: float):
        """Record transaction volume"""
        if self.enabled:
            self.volume_usd.labels(coin=coin, direction=direction).inc(amount_usd)

    def record_processing_time(self, coin: str, stage: str, seconds: float):
        """Record processing time"""
        if self.enabled:
            self.processing_time.labels(coin=coin, stage=stage).observe(seconds)

    def record_worker_cycle(self):
        """Record a worker cycle"""
        if self.enabled:
            self.worker_cycles.inc()
            self.worker_last_cycle.set(time.time())

    def record_worker_error(self, error_type: str):
        """Record a worker error"""
        if self.enabled:
            self.worker_errors.labels(error_type=error_type).inc()

    def record_rate_limit(self, limit_type: str):
        """Record a rate limit hit"""
        if self.enabled:
            self.rate_limit_hits.labels(limit_type=limit_type).inc()

    def record_exchange_request(self, endpoint: str, status: str, latency: float):
        """Record an exchange API request"""
        if self.enabled:
            self.exchange_requests.labels(endpoint=endpoint, status=status).inc()
            self.exchange_latency.labels(endpoint=endpoint).observe(latency)

    def record_blockchain_request(self, coin: str, status: str):
        """Record a blockchain explorer request"""
        if self.enabled:
            self.blockchain_requests.labels(coin=coin, status=status).inc()

    def set_active_users(self, count: int):
        """Set active users gauge"""
        if self.enabled:
            self.active_users.set(count)

    def record_new_user(self):
        """Record a new user registration"""
        if self.enabled:
            self.new_users.inc()

    def update_uptime(self):
        """Update uptime gauge"""
        if self.enabled:
            self.uptime.set(time.time() - self._start_time)


# Global metrics instance
metrics = Metrics()


# ==================== Alerting ====================

class AlertManager:
    """Simple alerting via Telegram"""

    # Alert cooldowns (don't spam)
    _alert_cooldowns = {}
    DEFAULT_COOLDOWN = 300  # 5 minutes

    @classmethod
    async def send_alert(cls, alert_type: str, message: str, cooldown: int = None):
        """Send an alert via Telegram (with cooldown)"""
        from libs.telegram_client import TelegramClient

        cooldown = cooldown or cls.DEFAULT_COOLDOWN
        now = time.time()

        # Check cooldown
        last_sent = cls._alert_cooldowns.get(alert_type, 0)
        if now - last_sent < cooldown:
            logger.debug(f"Alert {alert_type} suppressed (cooldown)")
            return

        try:
            telegram = TelegramClient(settings.telegram_bot_token, settings.admin_chat_id)
            full_message = f"🚨 **ALERT: {alert_type}**\n\n{message}"
            await telegram.send_message(settings.admin_chat_id, full_message)
            cls._alert_cooldowns[alert_type] = now
            logger.info(f"Alert sent: {alert_type}")
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")

    @classmethod
    async def alert_high_failure_rate(cls, failed: int, total: int):
        """Alert on high failure rate"""
        if total > 0 and failed / total > 0.1:  # More than 10% failures
            await cls.send_alert(
                "HIGH_FAILURE_RATE",
                f"⚠️ High failure rate detected!\n"
                f"Failed: {failed}/{total} ({failed/total*100:.1f}%)\n"
                f"Check worker logs for details."
            )

    @classmethod
    async def alert_stuck_transactions(cls, count: int):
        """Alert on stuck transactions"""
        if count > 0:
            await cls.send_alert(
                "STUCK_TRANSACTIONS",
                f"⚠️ {count} transactions stuck for >2 hours\n"
                f"Manual intervention may be required."
            )

    @classmethod
    async def alert_withdrawal_failed(cls, txid: str, reason: str):
        """Alert on withdrawal failure"""
        await cls.send_alert(
            f"WITHDRAWAL_FAILED_{txid[:8]}",
            f"❌ Withdrawal failed!\n"
            f"TXID: {txid[:24]}...\n"
            f"Reason: {reason}",
            cooldown=60  # Shorter cooldown for specific failures
        )

    @classmethod
    async def alert_large_swap(cls, user_id: int, amount_usd: float, coin: str):
        """Alert on large swap requiring approval"""
        await cls.send_alert(
            f"LARGE_SWAP_{user_id}",
            f"💰 Large swap detected!\n"
            f"User: {user_id}\n"
            f"Amount: ${amount_usd:.2f} ({coin})\n"
            f"⚠️ Manual approval may be required.",
            cooldown=60
        )
