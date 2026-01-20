"""Trading Pipeline - Async version for automated crypto trading"""
import asyncio
from typing import Optional
from app.logger import setup_logger
from app.models import Deposit, DepositStatus, CoinType
from app.config import settings
from app import db
from libs.mexc_client import MEXCClient
from libs.telegram_client import TelegramClient
from libs.explorer_client import ExplorerClient

logger = setup_logger(__name__)

# Initialize clients
mexc = MEXCClient(settings.mexc_api_key, settings.mexc_api_secret)
telegram = TelegramClient(settings.telegram_bot_token, settings.admin_chat_id)
explorer = ExplorerClient()


async def process_confirmed_deposit(deposit: Deposit) -> bool:
    """Process a confirmed deposit - sell crypto and withdraw"""
    try:
        logger.info(f"{'='*60}")
        logger.info(f"🔄 PIPELINE: Processing deposit {deposit.txid[:16]}...")
        logger.info(f"{'='*60}")
        
        logger.info(f"📊 Details:")
        logger.info(f"   Coin: {deposit.coin}")
        logger.info(f"   User ID: {deposit.user_id}")
        logger.info(f"   Target: {deposit.target_address}")
        logger.info(f"   Status: {deposit.status}")
        
        # Step 1: Get amount (should already be in DB from worker)
        amount = deposit.onchain_amount or deposit.amount
        
        if not amount or amount <= 0:
            # Try to load fresh from DB in case worker just updated it
            logger.info(f"🔍 Amount not in memory, reloading from DB...")
            fresh_deposit = await db.get_deposit(deposit.txid)
            if fresh_deposit:
                amount = fresh_deposit.onchain_amount or fresh_deposit.amount
                logger.info(f"✅ Loaded from DB: {amount} {deposit.coin}")
            
            # If still no amount, try blockchain as last resort
            if not amount or amount <= 0:
                logger.info(f"🔍 Not in DB either, fetching from blockchain...")
                lookup_address = getattr(deposit, 'deposit_address', None) or deposit.target_address
                amount = await explorer.get_transaction_amount(
                    CoinType(deposit.coin),
                    deposit.txid,
                    lookup_address
                )
                
                if amount and amount > 0:
                    await db.update_deposit_amount(deposit.txid, amount)
                    logger.info(f"✅ Got amount from blockchain: {amount} {deposit.coin}")
                else:
                    logger.error(f"❌ Could not get transaction amount from anywhere!")
                    await _notify_error(deposit, "Could not determine amount")
                    await db.update_deposit_status(deposit.txid, DepositStatus.PROCESSING_ERROR)
                    return False
        
        logger.info(f"💰 Amount to trade: {amount} {deposit.coin}")
        
        # Step 2: Sell crypto to USDT
        if deposit.coin == 'USDT':
            usdt_amount = amount
        else:
            if settings.dry_run:
                price = 42.0  # Simulated
                usdt_amount = amount * price * 0.999
                logger.info(f"🧪 DRY RUN: Would sell {amount} {deposit.coin} → {usdt_amount:.2f} USDT")
            else:
                logger.info(f"💱 LIVE: Selling {amount} {deposit.coin} on MEXC...")
                
                success, trade_result = await asyncio.to_thread(
                    mexc.sell_crypto_to_usdt,
                    deposit.coin,
                    amount
                )
                
                if not success:
                    error_msg = trade_result.get('error', 'Unknown error')
                    logger.error(f"❌ Trade failed: {error_msg}")
                    await _notify_error(deposit, f"Trade failed: {error_msg}")
                    await db.update_deposit_status(deposit.txid, DepositStatus.TRADE_FAILED)
                    return False
                
                usdt_amount = trade_result['usdt_received']
                logger.info(f"✅ Trade complete: {usdt_amount:.2f} USDT received")

                # Reset retry count on successful trade
                await db.reset_retry_count(deposit.txid)
        
        # Step 3: Calculate fees
        network_fee = 1.0
        commission = usdt_amount * (settings.commission_percent / 100)
        total_fees = network_fee + commission
        final_amount = usdt_amount - total_fees
        
        if final_amount <= 0:
            logger.error(f"❌ Amount too small after fees")
            await _notify_error(deposit, f"Amount too small: {usdt_amount:.2f} USDT")
            await db.update_deposit_status(deposit.txid, DepositStatus.AMOUNT_TOO_SMALL)
            return False
        
        logger.info(f"💵 Breakdown: {usdt_amount:.2f} USDT - ${commission:.2f} commission ({settings.commission_percent}%) - ${network_fee:.2f} network = ${final_amount:.2f} final")
        
        
        # Step 4: Withdrawal logic
        # XMR: Withdraw immediately (already fully confirmed on MEXC)
        # BTC/LTC/DASH: Two-tier (sell early, withdraw after full confs)
        
        # Store USDT amount in database
        await db.update_deposit_usdt(deposit.txid, usdt_amount, final_amount)
        
        if deposit.coin == CoinType.XMR:
            # XMR: Already 10+ confs on MEXC, withdraw immediately
            logger.info(f"💰 XMR detected - withdrawing immediately...")
            
            if settings.dry_run:
                logger.info(f"🧪 DRY RUN: Would withdraw {final_amount:.2f} USDT")
            else:
                success, result = mexc.withdraw_usdt_trc20(deposit.target_address, final_amount)
                if success:
                    withdraw_id = result.get('withdraw_id')
                    logger.info(f"✅ Withdrawal successful: {withdraw_id}")
                    await db.update_deposit_status(deposit.txid, DepositStatus.WITHDRAWN)
                    await _notify_success(deposit, final_amount, "USDT", withdraw_id)
                else:
                    logger.error(f"❌ Withdrawal failed: {result}")
                    await db.update_deposit_status(deposit.txid, DepositStatus.WITHDRAWAL_FAILED)
                    return False
        else:
            # BTC/LTC/DASH: Mark as SOLD, withdraw after full confirmations
            await db.update_deposit_status(deposit.txid, DepositStatus.SOLD)
            logger.info(f"✅ Marked as SOLD - withdrawal pending full confirmations")
        
        logger.info(f"{'='*60}")
        logger.info(f"✅ PIPELINE COMPLETE")
        logger.info(f"{'='*60}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Pipeline error for {deposit.txid[:16]}...: {str(e)}")
        logger.error(f"Traceback:", exc_info=True)
        await _notify_error(deposit, f"Processing error: {str(e)}")
    return False


async def _notify_success(deposit: Deposit, amount: float, coin: str, withdraw_id: str):
    """Notify user of successful withdrawal"""
    try:
        message = f"✅ Փոխանակումը ավարտված է!\n\n"
        message += f"💰 Ստացել եք: {amount:.2f} {coin}\n"
        message += f"📍 Հասցե: {deposit.target_address}\n"
        message += f"🆔 Withdrawal ID: {withdraw_id}\n\n"
        message += f"Շնորհակալություն! 🎉"
        
        await telegram.send_message(deposit.user_id, message)
        logger.info(f"User {deposit.user_id} notified of success")
    except Exception as e:
        logger.error(f"Failed to notify user: {e}")


async def _notify_error(deposit: Deposit, error: str):
    """Notify user of error"""
    try:
        message = f"⚠️ Խնդիր է առաջացել\n\n"
        message += f"Գործարք: {deposit.txid[:16]}...\n"
        message += f"Պատճառ: {error}\n\n"
        message += f"Մենք կուղղենք խնդիրը շուտով։"
        
        await telegram.send_message(deposit.user_id, message)
        logger.info(f"User {deposit.user_id} notified of error")
    except Exception as e:
        logger.error(f"Failed to notify user: {e}")


async def withdraw_usdt_only(deposit: Deposit) -> bool:
    """Withdraw USDT for an already-sold deposit"""
    from app.config import settings
    from libs.mexc_client import MEXCClient
    from libs.telegram_client import TelegramClient
    import asyncio
    
    logger.info(f"📤 Withdrawing USDT for {deposit.txid[:16]}...")
    
    try:
        mexc = MEXCClient(settings.mexc_api_key, settings.mexc_api_secret)
        telegram = TelegramClient(settings.telegram_bot_token, settings.admin_chat_id)
        
        # Get stored USDT amount from database
        if deposit.usdt_amount and deposit.usdt_amount > 0:
            usdt_amount = deposit.usdt_amount
            final_amount = deposit.final_usdt if deposit.final_usdt > 0 else usdt_amount * 0.94
            logger.info(f"💰 Using stored USDT: {usdt_amount:.2f} → {final_amount:.2f} final")
        else:
            # Fallback: shouldn't happen, but just in case
            logger.error(f"❌ No stored USDT amount! This shouldn't happen.")
            return False
        
        logger.info(f"💵 Final withdrawal: {final_amount:.2f} USDT")
        
        if settings.dry_run:
            logger.info(f"🧪 DRY RUN: Would withdraw {final_amount:.2f} USDT")
            return True
        
        # Actual withdrawal
        withdrawal_id = mexc.withdraw_usdt_trc20(deposit.target_address, final_amount)
        
        if withdrawal_id:
            logger.info(f"✅ Withdrawal successful: {withdrawal_id}")
            
            # Notify user
            await telegram.send_message(
                str(deposit.user_id),
                f"✅ Withdrawal complete!\n"
                f"Amount: {final_amount:.2f} USDT\n"
                f"Address: {deposit.target_address[:10]}...\n"
                f"Withdrawal ID: {withdrawal_id}"
            )
            
            return True
        else:
            logger.error("❌ Withdrawal failed")
            return False
            
    except Exception as e:
        logger.error(f"💥 Withdrawal error: {e}")
        return False
