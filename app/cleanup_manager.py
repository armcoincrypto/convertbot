"""Smart cleanup manager for invalid transactions"""
import asyncio
from datetime import datetime, timedelta
from typing import List
from app.logger import setup_logger
from app.models import DepositStatus
from app import db
from libs.explorer_client import explorer_client
from libs.telegram_client import TelegramClient
from app.config import settings

logger = setup_logger(__name__)
telegram = TelegramClient(settings.telegram_bot_token, settings.admin_chat_id)

class CleanupManager:
    """Manages automatic cleanup of problematic transactions"""
    
    # Configuration
    MAX_AMOUNT_FETCH_ATTEMPTS = 3  # Try 3 times to get amount
    MAX_EXPLORER_FAILURES = 5      # After 5 failures, mark as invalid
    STALE_HOURS = 24               # Auto-cleanup after 24 hours
    
    def __init__(self):
        self.attempt_tracker = {}  # Track retry attempts per txid
    
    async def check_and_cleanup(self) -> dict:
        """Main cleanup routine - returns stats"""
        stats = {
            'checked': 0,
            'cleaned': 0,
            'notified': 0
        }
        
        # 1. Check CONFIRMED deposits that can't get amount
        confirmed_deposits = await db.get_pending_deposits([DepositStatus.CONFIRMED])
        
        for deposit in confirmed_deposits:
            stats['checked'] += 1
            
            # Track attempts
            if deposit.txid not in self.attempt_tracker:
                self.attempt_tracker[deposit.txid] = {
                    'count': 0,
                    'first_seen': datetime.now()
                }
            
            tracker = self.attempt_tracker[deposit.txid]
            tracker['count'] += 1
            
            # Check if transaction is too old
            age_hours = (datetime.now() - tracker['first_seen']).total_seconds() / 3600
            
            # Decision logic
            should_cleanup = False
            reason = ""
            
            if tracker['count'] >= self.MAX_AMOUNT_FETCH_ATTEMPTS:
                # Can't get amount after multiple tries
                should_cleanup = True
                reason = f"Could not fetch amount after {tracker['count']} attempts"
            
            elif age_hours >= self.STALE_HOURS:
                # Transaction stuck for too long
                should_cleanup = True
                reason = f"Transaction stuck for {age_hours:.1f} hours"
            
            if should_cleanup:
                await self._cleanup_transaction(deposit, reason)
                stats['cleaned'] += 1
                stats['notified'] += 1
                # Remove from tracker
                del self.attempt_tracker[deposit.txid]
        
        # 2. Cleanup very old NEW/CONFIRMING deposits
        await self._cleanup_stale_unconfirmed()
        
        return stats
    
    async def _cleanup_transaction(self, deposit, reason: str):
        """Clean up a problematic transaction"""
        logger.warning(f"🧹 CLEANUP: {deposit.txid[:16]}... - {reason}")
        
        # Mark as INVALID (custom status for tracking)
        await db.update_deposit_status(deposit.txid, DepositStatus.PROCESSING_ERROR)
        
        # Notify operator
        try:
            msg = (
                f"🧹 AUTO-CLEANUP\n\n"
                f"TXID: {deposit.txid[:32]}...\n"
                f"Coin: {deposit.coin}\n"
                f"User: {deposit.user_id}\n"
                f"Reason: {reason}\n\n"
                f"Status changed to PROCESSING_ERROR.\n"
                f"User can now submit new transaction."
            )
            await telegram.send_message(settings.admin_chat_id, msg)
            logger.info(f"✅ Operator notified about cleanup")
        except Exception as e:
            logger.error(f"Failed to notify operator: {e}")
        
        # Optionally notify user
        try:
            user_msg = (
                f"⚠️ Խնդիր է առաջացել գործարքի հետ\n\n"
                f"TXID: {deposit.txid[:16]}...\n"
                f"Պատճառ: {reason}\n\n"
                f"Խնդրում ենք ստուգել TXID-ը և փորձել նորից։\n"
                f"Կամ կապվեք օպերատորի հետ: @Conodoperatorbot"
            )
            await telegram.send_message(deposit.user_id, user_msg)
        except:
            pass
    
    async def _cleanup_stale_unconfirmed(self):
        """Remove very old unconfirmed deposits"""
        cutoff = datetime.now() - timedelta(hours=self.STALE_HOURS)
        cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:%S')
        
        import aiosqlite
        async with aiosqlite.connect(db.get_db_path()) as conn:
            cursor = await conn.execute("""
                DELETE FROM deposits 
                WHERE status IN ('NEW', 'CONFIRMING') 
                AND inserted_at < ?
                AND confs = 0
            """, (cutoff_str,))
            deleted = cursor.rowcount
            await conn.commit()
            
            if deleted > 0:
                logger.info(f"🧹 Cleaned up {deleted} stale unconfirmed deposits")

# Global instance
cleanup_manager = CleanupManager()
