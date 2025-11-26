from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False, "extra": "ignore"}
    
    database_url: str = "sqlite:///swapbot.db"
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
    required_confs_dash: int = 4
    dry_run: bool = True
    commission_percent: float = 3.0  # 3% commission
    log_level: str = "INFO"
    
@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
