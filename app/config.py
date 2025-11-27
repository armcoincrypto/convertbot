from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False, "extra": "ignore"}

    database_url: str = "sqlite:///swapbot.db"  # Fixed: SQLite default
    mexc_api_key: str
    mexc_api_secret: str
    telegram_bot_token: str
    admin_chat_id: str
    addr_btc: str
    addr_ltc: str
    addr_dash: str
    addr_xmr: str
    required_confs_btc: int = 2
    required_confs_ltc: int = 4
    required_confs_dash: int = 12  # Fixed: Was 4, should be 12
    dry_run: bool = True
    commission_percent: float = 3.0  # 3% commission
    log_level: str = "INFO"

    # Rate limiting settings
    rate_limit_cooldown: int = 30  # Seconds between swaps per user
    daily_swap_limit: int = 10     # Max swaps per user per day
    daily_volume_limit: float = 10000.0  # Max USD volume per user per day

    # Redis settings (optional - falls back to in-memory if not available)
    redis_url: str = "redis://localhost:6379/0"

    # Monitoring settings
    metrics_enabled: bool = False
    metrics_port: int = 9090

    # Large swap threshold (requires manual approval)
    large_swap_threshold: float = 5000.0  # USD
    
@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
