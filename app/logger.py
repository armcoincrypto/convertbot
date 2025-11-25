import logging
import sys
import os
from logging.handlers import RotatingFileHandler

# Log directory - use /var/log/convertbot if running as root, else local logs/
LOG_DIR = "/var/log/convertbot" if os.geteuid() == 0 else os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")

def setup_logger(name: str, log_file: str = None):
    """Setup logger with both console and file output.

    Args:
        name: Logger name (usually __name__)
        log_file: Optional specific log file name. If None, uses 'convertbot.log'
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # Console handler (stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler with rotation
        try:
            os.makedirs(LOG_DIR, exist_ok=True)

            # Determine log file name based on module
            if log_file:
                file_name = log_file
            elif 'worker' in name:
                file_name = "worker.log"
            elif 'bot' in name or 'telegram' in name:
                file_name = "bot.log"
            else:
                file_name = "convertbot.log"

            log_path = os.path.join(LOG_DIR, file_name)
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=10*1024*1024,  # 10MB per file
                backupCount=5,  # Keep 5 backup files
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            # Also create an error-only log
            error_log_path = os.path.join(LOG_DIR, file_name.replace('.log', '-error.log'))
            error_handler = RotatingFileHandler(
                error_log_path,
                maxBytes=5*1024*1024,  # 5MB
                backupCount=3,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            logger.addHandler(error_handler)

        except PermissionError:
            # Fall back to local logs directory if no permission
            pass
        except Exception as e:
            print(f"Warning: Could not setup file logging: {e}")

    return logger
