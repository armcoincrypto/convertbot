"""Enhanced explorer with automatic retry"""
import asyncio
from typing import Optional
from app.models import CoinType
from libs.explorer_client import explorer_client
from app.logger import setup_logger

logger = setup_logger(__name__)

async def get_confirmations_with_retry(coin: CoinType, txid: str, max_retries: int = 3) -> Optional[int]:
    """Get confirmations with automatic retry on failure"""
    for attempt in range(max_retries):
        try:
            result = await explorer_client.get_confirmations(coin, txid)
            if result is not None:
                return result
            
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.info(f"Retry {attempt + 1}/{max_retries} in {wait_time}s...")
                await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
    
    return None
