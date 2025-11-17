"""Transaction validation rules"""
from typing import Tuple, Optional
from app.models import CoinType
from libs.mexc_client import MEXCClient
from app.config import settings

# Minimum transaction amount in USD
MIN_AMOUNT_USD = 19.0

def get_coin_price_usd(coin: CoinType) -> Optional[float]:
    """Get current price of coin in USD"""
    try:
        mexc = MEXCClient(settings.mexc_api_key, settings.mexc_api_secret)
        
        if coin == CoinType.DASH:
            return mexc.get_ticker_price("DASHUSDT")
        elif coin == CoinType.BTC:
            return mexc.get_ticker_price("BTCUSDT")
        elif coin == CoinType.LTC:
            return mexc.get_ticker_price("LTCUSDT")
        elif coin == CoinType.XMR:
            return mexc.get_ticker_price("XMRUSDT")
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
