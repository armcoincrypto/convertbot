"""
Structured Logging Module for Convertbot
Supports both human-readable and JSON formats
"""
import logging
import sys
import os
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any

# Log directory
LOG_DIR = "/var/log/convertbot" if os.geteuid() == 0 else os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "logs"
)

# Global context for correlation
_context: Dict[str, Any] = {}


def set_context(**kwargs):
    """Set global context fields that will be included in all log messages"""
    global _context
    _context.update(kwargs)


def clear_context():
    """Clear global context"""
    global _context
    _context = {}


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add global context
        if _context:
            log_data["context"] = _context.copy()

        # Add extra fields from record
        if hasattr(record, "txid"):
            log_data["txid"] = record.txid
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "coin"):
            log_data["coin"] = record.coin
        if hasattr(record, "extra_data"):
            log_data["data"] = record.extra_data

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


class ContextAdapter(logging.LoggerAdapter):
    """Logger adapter that supports extra context fields"""

    def process(self, msg, kwargs):
        # Merge extra fields
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs

    def with_context(self, **kwargs) -> "ContextAdapter":
        """Create a new adapter with additional context"""
        new_extra = {**self.extra, **kwargs}
        return ContextAdapter(self.logger, new_extra)


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    json_format: bool = False,
    level: int = logging.INFO
) -> ContextAdapter:
    """
    Setup logger with both console and file output.

    Args:
        name: Logger name (usually __name__)
        log_file: Optional specific log file name
        json_format: Use JSON formatting (recommended for production)
        level: Logging level

    Returns:
        ContextAdapter with extra field support
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return ContextAdapter(logger, {})

    # Choose formatter
    if json_format or os.getenv("LOG_FORMAT") == "json":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler with rotation
    try:
        os.makedirs(LOG_DIR, exist_ok=True)

        # Determine log file name
        if log_file:
            file_name = log_file
        elif "worker" in name:
            file_name = "worker.log"
        elif "bot" in name or "telegram" in name:
            file_name = "bot.log"
        else:
            file_name = "convertbot.log"

        log_path = os.path.join(LOG_DIR, file_name)

        # Main log file
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # JSON log file (always JSON for machine parsing)
        json_log_path = os.path.join(LOG_DIR, file_name.replace(".log", ".json.log"))
        json_handler = RotatingFileHandler(
            json_log_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        json_handler.setFormatter(JsonFormatter())
        logger.addHandler(json_handler)

        # Error-only log
        error_log_path = os.path.join(LOG_DIR, file_name.replace(".log", "-error.log"))
        error_handler = RotatingFileHandler(
            error_log_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)

    except PermissionError:
        pass
    except Exception as e:
        print(f"Warning: Could not setup file logging: {e}")

    return ContextAdapter(logger, {})


class TransactionLogger:
    """
    Specialized logger for transaction tracking.
    Ensures all transaction-related logs have proper context.
    """

    def __init__(self, base_logger: ContextAdapter):
        self.logger = base_logger

    def for_transaction(self, txid: str, coin: str = None, user_id: int = None):
        """Get logger with transaction context"""
        extra = {"txid": txid[:16] if txid else None}
        if coin:
            extra["coin"] = coin
        if user_id:
            extra["user_id"] = user_id
        return self.logger.with_context(**extra)

    def log_deposit_received(self, txid: str, coin: str, user_id: int, amount: float = None):
        """Log deposit received event"""
        self.logger.info(
            f"Deposit received: {coin} from user {user_id}",
            extra={"txid": txid, "coin": coin, "user_id": user_id, "extra_data": {"amount": amount}}
        )

    def log_confirmation_update(self, txid: str, coin: str, confs: int, required: int):
        """Log confirmation update"""
        self.logger.info(
            f"Confirmations: {confs}/{required}",
            extra={"txid": txid, "coin": coin, "extra_data": {"confs": confs, "required": required}}
        )

    def log_trade_executed(self, txid: str, coin: str, amount: float, usdt_received: float):
        """Log trade execution"""
        self.logger.info(
            f"Trade executed: {amount} {coin} -> {usdt_received} USDT",
            extra={"txid": txid, "coin": coin, "extra_data": {"amount": amount, "usdt": usdt_received}}
        )

    def log_withdrawal_sent(self, txid: str, user_id: int, amount: float, address: str):
        """Log withdrawal sent"""
        self.logger.info(
            f"Withdrawal sent: {amount} USDT to {address[:10]}...",
            extra={"txid": txid, "user_id": user_id, "extra_data": {"amount": amount, "address": address}}
        )

    def log_error(self, txid: str, error: str, stage: str = None):
        """Log transaction error"""
        self.logger.error(
            f"Transaction error: {error}",
            extra={"txid": txid, "extra_data": {"error": error, "stage": stage}}
        )


# Create default transaction logger
_default_logger = setup_logger("convertbot")
tx_logger = TransactionLogger(_default_logger)
