"""
ScalperBot Configuration
Pydantic-based settings loaded from .env file
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # MEXC API credentials
    mexc_api_key: str = ""
    mexc_api_secret: str = ""

    # Trading mode
    dry_run: bool = True

    # Trading pairs
    trading_pairs: List[str] = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]

    # Strategy parameters
    strategy_interval: int = 60  # Run strategy every N seconds
    data_poll_interval: int = 10  # Poll market data every N seconds

    # GREEN filter thresholds (momentum breakout strategy)
    green2_bb_period: int = 20
    green2_bb_std: float = 2.0
    green3_volume_threshold: float = 1.5  # Volume Z-score threshold
    green3_enabled: bool = False  # Disabled by default (market volume too low)
    green4_breakout_period: int = 10
    green4_breakout_buffer_bps: int = 10  # Basis points (0.1%)

    # Position sizing
    position_size_usd: float = 100.0  # Default position size
    max_positions: int = 3

    # Risk management
    daily_loss_limit_pct: float = 3.0  # Stop trading if down 3% for the day

    # Advanced risk parameters (Hybrid Approach)
    max_spread_bps: float = 6.0  # Max spread in basis points
    trail_stop_bps: float = 15.0  # Trail stop distance
    trail_activation_bps: float = 15.0  # Profit before trailing starts
    time_stop_seconds: int = 180  # Exit if not profitable after 3 min
    cooldown_after_loss_seconds: int = 300  # 5 min cooldown after loss

    # Database
    database_path: str = "scalperbot/trades.db"

    # Telegram (optional)
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Logging
    log_level: str = "INFO"
    log_file: str = "bot.log"


# Global settings instance
settings = Settings()
