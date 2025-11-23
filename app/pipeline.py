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
                    # NOTE: Don't notify user - TRADE_FAILED deposits are auto-retried every 2.5 min
                    # User will be notified only when they actually receive funds
                    await db.update_deposit_status(deposit.txid, DepositStatus.TRADE_FAILED)
                    return False
                
                usdt_amount = trade_result['usdt_received']
                logger.info(f"✅ Trade complete: {usdt_amount:.2f} USDT received")
        
        # Step 3: Calculate fees
        commission = usdt_amount * (settings.commission_percent / 100)
        mexc_withdrawal_fee = 1.0  # MEXC's TRC20 withdrawal fee (deducted by MEXC)

        # Amount we'll withdraw from MEXC (before their fee)
        withdrawal_amount = usdt_amount - commission

        # Amount user will actually receive (after MEXC deducts their fee)
        final_amount = withdrawal_amount - mexc_withdrawal_fee

        if final_amount <= 0:
            logger.error(f"❌ Amount too small after fees")
            await _notify_error(deposit, f"Amount too small: {usdt_amount:.2f} USDT")
            await db.update_deposit_status(deposit.txid, DepositStatus.AMOUNT_TOO_SMALL)
            return False

        logger.info(f"💵 Breakdown: {usdt_amount:.2f} USDT - ${commission:.2f} commission ({settings.commission_percent}%) = ${withdrawal_amount:.2f} to withdraw")
        logger.info(f"💵 User receives: ${withdrawal_amount:.2f} - ${mexc_withdrawal_fee:.2f} MEXC fee = ${final_amount:.2f} final")
        
        
        # Step 4: Withdrawal logic
        # XMR: Withdraw immediately (already fully confirmed on MEXC)
        # BTC/LTC/DASH: Two-tier (sell early, withdraw after full confs)

        # Store USDT amounts in database
        # usdt_amount: What we got from selling
        # withdrawal_amount: What we'll withdraw from MEXC (user receives this minus MEXC fee)
        await db.update_deposit_usdt(deposit.txid, usdt_amount, withdrawal_amount)
        
        if deposit.coin == CoinType.XMR:
            # XMR: Already 10+ confs on MEXC, mark as SOLD and withdraw immediately
            logger.info(f"💰 XMR detected - ready for immediate withdrawal...")
            await db.update_deposit_status(deposit.txid, DepositStatus.SOLD)
            logger.info(f"✅ Marked as SOLD - ready for withdrawal")

            # Use the same withdrawal function as BTC/LTC/DASH
            # This will check output_coin and withdraw USDT or TRX accordingly
            success = await withdraw_usdt_only(deposit)
            if success:
                await db.update_deposit_status(deposit.txid, DepositStatus.WITHDRAWN)
                logger.info(f"✅ XMR withdrawal complete!")
            else:
                logger.error(f"❌ XMR withdrawal failed")
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
    """Withdraw USDT or TRX for an already-sold deposit"""
    from app.config import settings
    from libs.mexc_client import MEXCClient
    from libs.telegram_client import TelegramClient
    import asyncio

    # Determine output coin (default to USDT for backward compatibility)
    output_coin = deposit.output_coin if hasattr(deposit, 'output_coin') and deposit.output_coin else 'USDT'
    logger.info(f"📤 Withdrawing {output_coin} for {deposit.txid[:16]}...")

    try:
        mexc = MEXCClient(settings.mexc_api_key, settings.mexc_api_secret)
        telegram = TelegramClient(settings.telegram_bot_token, settings.admin_chat_id)

        # Get stored USDT amount from database
        if deposit.usdt_amount and deposit.usdt_amount > 0:
            usdt_amount = deposit.usdt_amount  # What we got from selling
            withdrawal_amount = deposit.final_usdt if deposit.final_usdt > 0 else usdt_amount * 0.94
            mexc_fee = 1.0  # MEXC's withdrawal fee (TRC20/TRX)
            final_amount = withdrawal_amount - mexc_fee  # What user actually receives
            logger.info(f"💰 Stored: {usdt_amount:.2f} USDT → Withdraw: {withdrawal_amount:.2f} → User receives: {final_amount:.2f} (after MEXC {mexc_fee:.2f} fee)")
        else:
            # Fallback: shouldn't happen, but just in case
            logger.error(f"❌ No stored USDT amount! This shouldn't happen.")
            return False

        if settings.dry_run:
            logger.info(f"🧪 DRY RUN: Would withdraw {final_amount:.2f} {output_coin}")
            return True

        # Handle TRX withdrawals (buy TRX with USDT first)
        if output_coin == 'TRX':
            logger.info(f"💱 Converting USDT → TRX on MEXC...")

            # Buy TRX with the full withdrawal amount (MEXC will deduct fee from TRX)
            success, result = mexc.buy_crypto_with_usdt('TRX', withdrawal_amount)
            if not success:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"❌ Failed to buy TRX: {error_msg}")
                return False

            trx_amount = result.get('amount', 0)
            logger.info(f"✅ Bought {trx_amount:.2f} TRX with {withdrawal_amount:.2f} USDT")

            # Withdraw TRX (MEXC may deduct a small TRX fee, typically ~1 TRX)
            success, result = mexc.withdraw_trx(deposit.target_address, trx_amount)
            if success:
                withdrawal_id = result.get('withdraw_id', 'N/A')
                logger.info(f"✅ TRX Withdrawal successful: {withdrawal_id}")

                # Estimate what user receives (TRX fee is usually ~1 TRX)
                trx_fee_estimate = 1.0
                estimated_received = trx_amount - trx_fee_estimate

                # Notify user in Armenian
                await telegram.send_message(
                    str(deposit.user_id),
                    f"✅ Փոխանակումը ավարտված է!\n\n"
                    f"💰 Ստացել եք: ~{estimated_received:.2f} TRX\n"
                    f"📍 Հասցե: {deposit.target_address}\n"
                    f"🆔 Withdrawal ID: {withdrawal_id}\n\n"
                    f"Շնորհակալություն! 🎉"
                )
                return True
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"❌ TRX Withdrawal failed: {error_msg}")
                return False

        # Handle USDT withdrawals
        else:
            logger.info(f"💵 Withdrawing {withdrawal_amount:.2f} USDT (user receives {final_amount:.2f} after MEXC {mexc_fee:.2f} fee)")

            # Withdraw the full withdrawal_amount (MEXC will deduct their 1.0 USDT fee)
            success, result = mexc.withdraw_usdt_trc20(deposit.target_address, withdrawal_amount)

            if success:
                withdrawal_id = result.get('withdraw_id', 'N/A')
                logger.info(f"✅ Withdrawal successful: {withdrawal_id}")

                # Notify user of the ACTUAL amount they'll receive (after MEXC fee)
                await telegram.send_message(
                    str(deposit.user_id),
                    f"✅ Փոխանակումը ավարտված է!\n\n"
                    f"💰 Ստացել եք: {final_amount:.2f} USDT\n"
                    f"📍 Հասցե: {deposit.target_address}\n"
                    f"🆔 Withdrawal ID: {withdrawal_id}\n\n"
                    f"Շնորհակալություն! 🎉"
                )

                return True
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"❌ Withdrawal failed: {error_msg}")
                return False

    except Exception as e:
        logger.error(f"💥 Withdrawal error: {e}")
        return False
