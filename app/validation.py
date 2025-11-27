"""Transaction validation rules"""
import time
from typing import Tuple, Optional
from app.models import CoinType
from libs.mexc_client import MEXCClient
from app.config import settings

# Minimum transaction amount in USD
MIN_AMOUNT_USD = 19.0

# Price cache (60 second TTL)
_price_cache = {}
_cache_ttl = 60

# Singleton MEXC client
_mexc_client = None

def _get_mexc_client():
    """Get or create singleton MEXC client"""
    global _mexc_client
    if _mexc_client is None:
        _mexc_client = MEXCClient(settings.mexc_api_key, settings.mexc_api_secret)
    return _mexc_client

def get_coin_price_usd(coin: CoinType) -> Optional[float]:
    """Get current price of coin in USD (with caching)"""
    global _price_cache

    coin_str = coin.value if hasattr(coin, 'value') else str(coin)
    now = time.time()

    # Check cache
    if coin_str in _price_cache:
        cached_price, cached_time = _price_cache[coin_str]
        if now - cached_time < _cache_ttl:
            return cached_price

    try:
        mexc = _get_mexc_client()

        symbol = f"{coin_str}USDT"
        price = mexc.get_ticker_price(symbol)

        if price:
            _price_cache[coin_str] = (price, now)
            return price
    except:
        pass
    return None

def validate_amount(coin: CoinType, amount: float) -> Tuple[bool, str]:
    """
    Validate if transaction meets minimum amount
    Returns: (is_valid, error_message)
    """
    price = get_coin_price_usd(coin)
    
    if price is None:
        return False, "❌ Չհաջողվեց ստանալ գնանշումը"
    
    usd_value = amount * price
    
    if usd_value < MIN_AMOUNT_USD:
        return False, f"❌ Նվազագույն գումար: ${MIN_AMOUNT_USD}\nՁեր գումարը: ${usd_value:.2f}"
    
    return True, ""

def get_minimum_amount(coin: CoinType) -> str:
    """Get minimum amount for a coin in readable format"""
    price = get_coin_price_usd(coin)
    
    if price:
        min_coins = MIN_AMOUNT_USD / price
        return f"{min_coins:.4f} {coin.value} (≈${MIN_AMOUNT_USD})"
    
    return f"${MIN_AMOUNT_USD}"
