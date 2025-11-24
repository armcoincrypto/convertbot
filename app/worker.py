"""Main worker with detailed logging."""
import asyncio
import aiosqlite
from typing import Dict, Any
from app.logger import setup_logger
from app.config import settings
from app import db
from app.models import DepositStatus, CoinType
from libs.explorer_client import explorer_client
from app.validation import validate_amount
from libs.mexc_client import MEXCClient
from libs.telegram_client import TelegramClient

logger = setup_logger(__name__)

mexc = MEXCClient(settings.mexc_api_key, settings.mexc_api_secret)
telegram = TelegramClient(settings.telegram_bot_token, settings.admin_chat_id)

# Add early sell tracking
EARLY_SOLD_AMOUNTS = {}  # txid -> usdt_amount


def get_db_path():
    """Get database path from config."""
    db_url = settings.database_url
    if db_url.startswith('sqlite'):
        return db_url.replace('sqlite:///', '')
    return 'swapbot.db'


async def cleanup_old_deposits():
    """Delete deposits older than 1 hour with no confirmations"""
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(hours=1)
    cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:%S')
    
    async with aiosqlite.connect(get_db_path()) as conn:
        # Delete old NEW/CONFIRMING deposits
        await conn.execute("""
            DELETE FROM deposits 
            WHERE status IN ('NEW', 'CONFIRMING') 
            AND inserted_at < ?
            AND confs = 0
        """, (cutoff_str,))
        
        deleted = conn.total_changes
        await conn.commit()
        
        if deleted > 0:
            logger.info(f"🧹 Cleaned up {deleted} old unconfirmed deposits")


async def retry_failed_deposits():
    """Retry deposits stuck in TRADE_FAILED or WITHDRAWAL_FAILED status with attempt tracking"""
    MAX_ATTEMPTS = 5

    try:
        logger.info("🔄 Checking for failed deposits to retry...")

        # Retry TRADE_FAILED deposits (sell failed)
        trade_failed = await db.get_deposits_by_status(DepositStatus.TRADE_FAILED)
        if trade_failed:
            logger.info(f"🔁 Found {len(trade_failed)} TRADE_FAILED deposits, checking attempts...")
            for deposit in trade_failed:
                # Get attempt count (handle deposits without attempt_count column)
                attempt_count = getattr(deposit, 'attempt_count', 0) or 0

                if attempt_count >= MAX_ATTEMPTS:
                    logger.error(f"   ❌ Max attempts reached for {deposit.txid[:16]}... (attempted {attempt_count} times)")
                    await db.update_deposit_status(deposit.txid, DepositStatus.PROCESSING_ERROR)
                    # TODO: Notify admin
                    continue

                logger.info(f"   → Retrying trade: {deposit.txid[:16]}... (attempt {attempt_count + 1}/{MAX_ATTEMPTS})")
                await db.increment_attempt_count(deposit.txid)
                await db.update_deposit_status(deposit.txid, DepositStatus.CONFIRMED)
            logger.info(f"✅ Processed {len(trade_failed)} TRADE_FAILED deposits")

        # Retry WITHDRAWAL_FAILED deposits (withdrawal failed)
        withdrawal_failed = await db.get_deposits_by_status(DepositStatus.WITHDRAWAL_FAILED)
        if withdrawal_failed:
            logger.info(f"🔁 Found {len(withdrawal_failed)} WITHDRAWAL_FAILED deposits, checking attempts...")
            for deposit in withdrawal_failed:
                # Get attempt count (handle deposits without attempt_count column)
                attempt_count = getattr(deposit, 'attempt_count', 0) or 0

                if attempt_count >= MAX_ATTEMPTS:
                    logger.error(f"   ❌ Max attempts reached for {deposit.txid[:16]}... (attempted {attempt_count} times)")
                    await db.update_deposit_status(deposit.txid, DepositStatus.PROCESSING_ERROR)
                    # TODO: Notify admin
                    continue

                logger.info(f"   → Retrying withdrawal: {deposit.txid[:16]}... (attempt {attempt_count + 1}/{MAX_ATTEMPTS})")
                await db.increment_attempt_count(deposit.txid)
                await db.update_deposit_status(deposit.txid, DepositStatus.SOLD)
            logger.info(f"✅ Processed {len(withdrawal_failed)} WITHDRAWAL_FAILED deposits")

        if not trade_failed and not withdrawal_failed:
            logger.info("✅ No failed deposits to retry")

    except Exception as e:
        logger.error(f"❌ Error retrying failed deposits: {e}")


async def worker_cycle() -> Dict[str, Any]:
    """Main worker cycle with detailed logging."""
    logger.info("="*60)
    logger.info("🔄 Starting worker cycle")
    logger.info(f"Mode: {'DRY_RUN' if settings.dry_run else 'LIVE'}")
    
    try:
        deposits = await db.get_pending_deposits()
        logger.info(f"📊 Found {len(deposits)} pending deposits")
        
        processed = confirmed = 0
        
        for i, deposit in enumerate(deposits, 1):
            logger.info(f"\n--- Processing deposit {i}/{len(deposits)} ---")
            logger.info(f"TXID: {deposit.txid[:16]}...")
            logger.info(f"Coin: {deposit.coin.value}")
            logger.info(f"Status: {deposit.status.value}")
            logger.info(f"User: {deposit.user_id}")
            logger.info(f"Confirmations: {deposit.confs}/{deposit.required_confs}")
            
            try:
                if deposit.status in [DepositStatus.NEW, DepositStatus.CONFIRMING]:
                    logger.info(f"🔍 Checking blockchain for confirmations...")
                    
                    confs = await explorer_client.get_confirmations(deposit.coin, deposit.txid)
                    
                    # Check for fake transaction
                    if confs == -1:
                        logger.error(f"❌ FAKE TRANSACTION DETECTED: {deposit.txid[:16]}...")
                        await db.update_deposit_status(deposit.txid, DepositStatus.PROCESSING_ERROR)
                        await telegram.send_message(
                            deposit.user_id,
                            "❌ Սխալ գործարք\n\nԱյս գործարքը չի գտնվել blockchain-ում։\nԽնդրում ենք ստուգել txid-ը։"
                        )
                        continue
                    
                    if confs is None:
                        logger.warning(f"⚠️  Could not get confirmations from explorer")
                        # XMR: Check MEXC deposit history
                        if deposit.coin == CoinType.XMR:
                            logger.info("💰 XMR: Checking MEXC deposit history...")
                            try:
                                deposits_list = mexc.get_deposit_history(coin="XMR", limit=50)
                                matching = [d for d in deposits_list if d.get('txId') == deposit.txid]
                                
                                if matching:
                                    mexc_deposit = matching[0]
                                    xmr_amount = float(mexc_deposit['amount'])
                                    logger.info(f"✅ Found XMR deposit on MEXC: {xmr_amount} XMR (status {mexc_deposit['status']})")
                                    
                                    await db.update_deposit_amount(deposit.txid, xmr_amount)
                                    await db.update_deposit_confs(deposit.txid, 10)
                                    await db.update_deposit_status(deposit.txid, DepositStatus.CONFIRMED)
                                    logger.info(f"✅ XMR marked CONFIRMED with 10 confs")
                                    continue
                                else:
                                    logger.info(f"⏳ XMR deposit not yet on MEXC")
                            except Exception as e:
                                logger.error(f"❌ XMR deposit history check error: {e}")
                        continue
                    
                    logger.info(f"✅ Got {confs} confirmations from blockchain")
                    
                    # Two-stage system: Sell at minimum confs ONLY if on MEXC
                    EARLY_SELL_CONFS = 2 if deposit.coin != CoinType.DASH else deposit.required_confs
                    
                    if confs >= EARLY_SELL_CONFS and deposit.status == DepositStatus.CONFIRMING:
                        logger.info(f"💰 EARLY SELL! Processing at {confs} confs (price protection)")
                        await db.update_deposit_status(deposit.txid, DepositStatus.CONFIRMED, confs)
                        continue  # Skip further processing this cycle
                    
                    elif confs >= deposit.required_confs:
                        logger.info(f"🎉 FULLY CONFIRMED! {confs} >= {deposit.required_confs}")
                        await db.update_deposit_status(deposit.txid, DepositStatus.CONFIRMED, confs)
                        confirmed += 1
                        # NOTE: No notification here - user will be notified when they actually receive funds
                    else:
                        logger.info(f"⏳ Still waiting: {confs}/{deposit.required_confs}")
                        await db.update_deposit_status(deposit.txid, DepositStatus.CONFIRMING, confs)
                    
                    processed += 1

                elif deposit.status == DepositStatus.CONFIRMED:
                    logger.info(f"💰 Deposit is CONFIRMED, fetching amount...")
                    
                    # Get amount from blockchain if not set
                    onchain_amount = deposit.onchain_amount
                    if not onchain_amount or onchain_amount <= 0:
                        # Get the deposit address for this coin from config
                        deposit_address = {
                            'BTC': settings.addr_btc,
                            'LTC': settings.addr_ltc,
                            'DASH': settings.addr_dash,
                            'XMR': settings.addr_xmr
                        }.get(deposit.coin)
                        
                        onchain_amount = await explorer_client.get_transaction_amount(
                            CoinType(deposit.coin),
                            deposit.txid,
                            deposit_address
                        )
                        if onchain_amount and onchain_amount > 0:
                            await db.update_deposit_amount(deposit.txid, onchain_amount)
                            logger.info(f"✅ Amount: {onchain_amount} {deposit.coin}")
                        else:
                            logger.error(f"❌ Could not get amount")
                            continue
                    
                    # Check if already sold early
                    if deposit.txid in EARLY_SOLD_AMOUNTS:
                        logger.info(f"💰 Using early-sold USDT: {EARLY_SOLD_AMOUNTS[deposit.txid]['usdt']:.2f}")
                        # Skip to withdrawal with pre-sold USDT
                        # (Pipeline will handle this)
                    
                    # Validate minimum amount ($20)
                    is_valid, error_msg = validate_amount(CoinType(deposit.coin), onchain_amount)
                    if not is_valid:
                        logger.error(f"❌ Amount too small: {onchain_amount} {deposit.coin}")
                        await db.update_deposit_status(deposit.txid, DepositStatus.AMOUNT_TOO_SMALL)
                        
                        # Notify user
                        try:
                            telegram_client = TelegramClient(settings.telegram_bot_token, settings.admin_chat_id)
                            msg = (
                                f"⚠️ Գումարը բավարար չէ\n\n"
                                f"{error_msg}\n\n"
                                f"💡 Նվազագույն $20 է պետք, որպեսզի\n"
                                f"   հետո հանենք 3% + $1 միջնորդավճար։\n"
                                f"   Դուք կստանաք ~$18 USDT\n\n"
                                f"📱 Կապվեք օպերատորի հետ:\n"
                                f"@Conodoperatorbot\n\n"
                                f"Մենք կկատարենք փոխանակումը ձեռքով։\n\n"
                                f"TXID: {deposit.txid[:16]}..."
                            )
                            await telegram_client.send_message(deposit.user_id, msg)
                            logger.info(f"✅ Sent 'contact operator' notification to user {deposit.user_id}")
                            
                            # Notify operator
                            try:
                                from libs.mexc_client import MEXCClient
                                price = MEXCClient(settings.mexc_api_key, settings.mexc_api_secret).get_ticker_price(f"{deposit.coin.value if hasattr(deposit.coin, 'value') else deposit.coin}USDT")
                                usd_val = onchain_amount * price if price else 0
                                operator_msg = (
                                    f"🔔 ՈՒՇԱԴՐՈՒԹՅՈՒՆ: Փոքր գումար\n\n"
                                    f"👤 User: {deposit.user_id}\n"
                                    f"💰 Գումար: ${usd_val:.2f} ({onchain_amount} {deposit.coin.value if hasattr(deposit.coin, 'value') else deposit.coin})\n"
                                    f"📍 Հասցե: {deposit.target_address}\n"
                                    f"🔗 TXID: {deposit.txid[:32]}...\n\n"
                                    f"Օգտատերը կապվելու է @Conodoperatorbot հետ։"
                                )
                                await telegram_client.send_message(settings.admin_chat_id, operator_msg)
                                logger.info(f"✅ Notified operator about small amount")
                            except Exception as e:
                                logger.error(f"❌ Failed to notify operator: {e}")
                        except Exception as e:
                            logger.error(f"❌ Failed to send notification: {e}")
                        continue
                    
                    logger.info(f"💰 Amount validated, starting pipeline...")
                    
                    from app.pipeline import process_confirmed_deposit
                    
                    logger.info(f"📈 Calling pipeline for {deposit.txid[:16]}...")
                    success = await process_confirmed_deposit(deposit)
                    
                    if success:
                        logger.info(f"✅ Pipeline completed successfully!")
                    else:
                        logger.error(f"❌ Pipeline failed!")

                elif deposit.status == DepositStatus.SOLD:
                    logger.info(f"💰 Deposit SOLD, checking if ready for withdrawal...")
                    
                    # XMR has no public blockchain - it's already confirmed on MEXC
                    if deposit.coin == CoinType.XMR:
                        confs = deposit.required_confs  # Always 10 when on MEXC
                        logger.info(f"✅ XMR on MEXC - ready for withdrawal")
                    else:
                        # For BTC/LTC/DASH - check blockchain
                        try:
                            confs = await explorer_client.get_confirmations(
                                CoinType(deposit.coin),
                                deposit.txid
                            )
                            if confs is not None and confs >= 0:
                                logger.info(f"✅ Got {confs} confirmations from blockchain")
                                await db.update_deposit_confs(deposit.txid, confs)
                            else:
                                # Invalid result, use database
                                confs = deposit.confs
                                logger.info(f"⚠️  Invalid blockchain result, using database confs: {confs}")
                        except Exception as e:
                            # Use database confs if blockchain fails
                            logger.warning(f"⚠️  Blockchain check failed: {e}")
                            confs = deposit.confs
                            logger.info(f"⚠️  Using database confs: {confs}")
                    
                    if confs and confs >= deposit.required_confs:
                        logger.info(f"🎉 READY FOR WITHDRAWAL! {confs} >= {deposit.required_confs}")
                        
                        # Withdraw the USDT
                        from app.pipeline import withdraw_usdt_only
                        success = await withdraw_usdt_only(deposit)
                        
                        if success:
                            await db.update_deposit_status(deposit.txid, DepositStatus.WITHDRAWN)
                            logger.info(f"✅ Withdrawal complete!")
                        else:
                            logger.error(f"❌ Withdrawal failed")
                    else:
                        logger.info(f"⏳ Waiting for withdrawal: {confs}/{deposit.required_confs}")
                    processed += 1
                    
            except Exception as e:
                logger.error(f"❌ ERROR processing deposit {deposit.txid[:16]}...")
                logger.error(f"Error type: {type(e).__name__}")
                logger.error(f"Error message: {str(e)}")
                import traceback
                logger.error(f"Traceback:\n{traceback.format_exc()}")
        
        result = {"processed": processed, "confirmed": confirmed}
        logger.info(f"\n✅ Worker cycle completed")
        logger.info(f"Summary: Processed={processed}, Confirmed={confirmed}")
        logger.info("="*60 + "\n")
        
        return result
        
    except Exception as e:
        logger.error(f"💥 FATAL ERROR in worker cycle!")
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return {"processed": 0, "confirmed": 0, "error": str(e)}


async def main():
    """Main worker loop with auto-retry for failed deposits"""
    logger.info("="*60)
    logger.info("🚀 WORKER STARTING")
    logger.info("="*60)
    logger.info(f"Mode: {'DRY_RUN' if settings.dry_run else 'LIVE'}")
    logger.info(f"Supported coins: BTC, LTC, DASH, XMR")
    logger.info(f"Auto-retry: TRADE_FAILED and WITHDRAWAL_FAILED deposits every 5 cycles (2.5 min)")
    logger.info("="*60)

    cycle_count = 0

    while True:
        try:
            cycle_count += 1

            # Every 5th cycle (2.5 minutes), retry failed deposits
            if cycle_count % 5 == 0:
                await retry_failed_deposits()
            
            logger.info(f"\n🔄 Starting worker cycle #{cycle_count}...")
            result = await worker_cycle()
            logger.info(f"Cycle result: {result}")
            
            # Sleep between cycles
            await asyncio.sleep(30)  # Check every 30 seconds
            
        except KeyboardInterrupt:
            logger.info("\n👋 Worker stopped by user")
            break
        except Exception as e:
            logger.error(f"💥 Worker error: {e}")
            import traceback
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            await asyncio.sleep(60)  # Wait longer on error


if __name__ == "__main__":
    asyncio.run(main())
