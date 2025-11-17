"""Blockchain transaction verification"""
from typing import Optional
from app.models import CoinType
from libs.explorer_client import ExplorerClient
from app.logger import setup_logger

logger = setup_logger(__name__)
explorer = ExplorerClient()


async def verify_transaction_exists(coin: CoinType, txid: str) -> bool:
    """
    Verify transaction actually exists on blockchain.
    Returns True only if transaction is confirmed to exist (even with 0 confs).
    Returns False if transaction is fake/not found.
    """
    logger.info(f"🔍 Verifying {coin.value} transaction exists: {txid[:16]}...")
    
    # Try to get transaction amount (proves it exists)
    amount = await explorer.get_transaction_amount(coin, txid, "dummy_address")
    
    if amount is None:
        # Transaction doesn't exist
        logger.error(f"❌ Transaction NOT FOUND on blockchain!")
        return False
    
    logger.info(f"✅ Transaction verified on blockchain")
    return True
