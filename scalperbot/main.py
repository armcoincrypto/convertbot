"""
ScalperBot - Main Entry Point
Cryptocurrency momentum breakout trading bot
"""
import asyncio
import logging
import signal
import sys
from datetime import datetime

from scalperbot.config import settings
from scalperbot.db import TradeDB
from scalperbot.exchanges.adapter import MEXCAdapter
from scalperbot.datafeed.candle_store import CandleStore
from scalperbot.datafeed.orderbook import OrderBook
from scalperbot.datafeed.rest_poller import RESTPoller
from scalperbot.strategies.momentum_breakout import MomentumBreakoutStrategy
from scalperbot.exec.router import OrderRouter
from scalperbot.ops.pos_size import PositionSizer
from scalperbot.risk.breaker import RiskBreaker
from scalperbot.position_manager import PositionManager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class ScalperBot:
    """
    Main trading bot class
    Orchestrates all components and runs trading loop
    """

    def __init__(self):
        logger.info("="*80)
        logger.info("🚀 ScalperBot Initializing...")
        logger.info(f"Mode: {'🔶 DRY_RUN' if settings.dry_run else '🟢 LIVE'}")
        logger.info(f"Trading pairs: {settings.trading_pairs}")
        logger.info("="*80)

        # Initialize components
        self.db = TradeDB(settings.database_path)
        self.exchange = MEXCAdapter(
            settings.mexc_api_key,
            settings.mexc_api_secret,
            dry_run=settings.dry_run
        )
        self.candle_store = CandleStore()
        self.orderbook = OrderBook()
        self.poller = RESTPoller(
            self.exchange,
            self.candle_store,
            self.orderbook,
            settings.trading_pairs,
            settings.data_poll_interval
        )
        self.strategy = MomentumBreakoutStrategy(self.candle_store)
        self.router = OrderRouter(self.exchange, self.orderbook)
        self.position_sizer = PositionSizer()
        self.risk_breaker = RiskBreaker(self.db)
        self.position_manager = PositionManager(settings)

        # State
        self.running = False
        self.poller_task = None

    async def initialize(self):
        """Initialize bot (fetch balance, set risk params, etc.)"""
        logger.info("🔧 Initializing bot components...")

        # Get starting balance for risk breaker
        try:
            balance = self.exchange.fetch_balance()
            usdt_balance = balance.get('USDT', {}).get('free', 0)
            self.risk_breaker.set_starting_balance(usdt_balance)
            logger.info(f"💰 USDT Balance: ${usdt_balance:.2f}")
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch balance: {e}")
            self.risk_breaker.set_starting_balance(1000.0)  # Default

        logger.info("✅ Initialization complete")

    async def trading_loop(self):
        """Main trading loop - runs strategy and executes trades"""
        logger.info(f"🔄 Trading loop started (interval: {settings.strategy_interval}s)")

        cycle = 0
        while self.running:
            cycle += 1
            logger.info(f"\n{'='*80}")
            logger.info(f"🔄 Strategy Cycle #{cycle} - {datetime.utcnow().isoformat()}")
            logger.info(f"{'='*80}")

            try:
                # Check risk breaker
                if not self.risk_breaker.can_trade():
                    logger.error("⛔ Risk breaker active - skipping trading")
                    await asyncio.sleep(settings.strategy_interval)
                    continue

                # Display data summary
                logger.info(self.candle_store.summary())
                logger.info(self.orderbook.summary())
                logger.info(self.position_manager.summary())

                # Check exits for open positions
                await self.check_position_exits()

                # Run strategy for all symbols
                signals = self.strategy.run_for_all_symbols(settings.trading_pairs)

                # Execute signals
                for signal in signals:
                    await self.execute_signal(signal)

            except Exception as e:
                logger.error(f"❌ Error in trading loop: {e}", exc_info=True)

            # Sleep until next cycle
            await asyncio.sleep(settings.strategy_interval)

    async def check_position_exits(self):
        """Check and execute exits for open positions"""
        for symbol in list(self.position_manager.positions.keys()):
            try:
                # Get current price
                mid_price = self.orderbook.get_mid_price(symbol)
                if not mid_price:
                    continue

                # Update position with current price (for trailing stop)
                self.position_manager.update_position(symbol, mid_price)

                # Check if should exit
                exit_reason = self.position_manager.check_exits(symbol, mid_price)

                if exit_reason:
                    await self.close_position(symbol, mid_price, exit_reason)

            except Exception as e:
                logger.error(f"❌ Error checking exit for {symbol}: {e}", exc_info=True)

    async def close_position(self, symbol: str, exit_price: float, reason: str):
        """Close a position"""
        position = self.position_manager.get_position(symbol)
        if not position:
            return

        logger.info(f"\n{'='*60}")
        logger.info(f"🔴 CLOSING POSITION: {symbol} @ {exit_price:.4f}")
        logger.info(f"Reason: {reason}")
        logger.info(f"{'='*60}")

        if settings.dry_run:
            logger.info(f"🔶 [DRY_RUN] Would close {position.quantity:.6f} {symbol}")
            closed_pos = self.position_manager.close_position(symbol, exit_price, reason)
            self.db.update_trade_pnl(closed_pos.trade_id,
                                     ((exit_price - closed_pos.entry_price) / closed_pos.entry_price) * 10000)
            return

        # Place market order to close
        side = 'sell' if position.side == 'buy' else 'buy'
        order = self.router.place_market_order(symbol, side, position.quantity)

        if order:
            closed_pos = self.position_manager.close_position(symbol, exit_price, reason)
            pnl_bps = ((exit_price - closed_pos.entry_price) / closed_pos.entry_price) * 10000
            self.db.update_trade_pnl(closed_pos.trade_id, pnl_bps)
            self.position_sizer.decrement_positions()
            logger.info(f"✅ Position closed successfully")
        else:
            logger.error(f"❌ Failed to close position")

    async def execute_signal(self, signal: dict):
        """Execute a trading signal"""
        symbol = signal['symbol']
        action = signal['action']
        price = signal['price']

        logger.info(f"\n{'*'*60}")
        logger.info(f"📢 EXECUTING SIGNAL: {action} {symbol} @ {price:.4f}")
        logger.info(f"{'*'*60}")

        try:
            # Pre-trade filter 1: Check if already in position
            if self.position_manager.has_position(symbol):
                logger.warning(f"⚠️ Already in position for {symbol}")
                return

            # Pre-trade filter 2: Check cooldown
            if self.position_manager.is_in_cooldown(symbol):
                logger.warning(f"⚠️ {symbol} in cooldown after loss")
                return

            # Pre-trade filter 3: Check spread
            spread_bps = self.orderbook.get_spread_bps(symbol)
            if spread_bps and spread_bps > settings.max_spread_bps:
                logger.warning(f"⚠️ Spread too wide: {spread_bps:.1f} bps > {settings.max_spread_bps} bps")
                return

            logger.info(f"✅ Pre-trade checks passed (spread: {spread_bps:.1f} bps)")

            # Calculate position size
            pos_size = self.position_sizer.calculate_size(symbol, price)

            if not pos_size['can_trade']:
                logger.warning(f"⚠️ Cannot trade: {pos_size['reason']}")
                return

            quantity = pos_size['quantity']
            notional_usd = pos_size['notional_usd']

            logger.info(f"Position size: {quantity:.6f} {symbol.split('/')[0]} (${notional_usd:.2f})")

            # Log trade to database (NEW status)
            trade_id = self.db.log_trade(
                symbol=symbol,
                side='buy' if action == 'BUY' else 'sell',
                price=price,
                quantity=quantity,
                notional=notional_usd,
                signal_reason=signal.get('reason', ''),
                status='NEW'
            )

            logger.info(f"Trade logged to database: ID={trade_id}")

            if settings.dry_run:
                logger.info(f"🔶 [DRY_RUN] Would place {action} order for {quantity:.6f} {symbol}")
                self.db.update_trade_status(trade_id, 'DRY_RUN')
                # Track position in DRY_RUN mode too
                self.position_manager.open_position(symbol, price, quantity, 'buy', trade_id)
                self.position_sizer.increment_positions()
                return

            # Place market order
            side = 'buy' if action == 'BUY' else 'sell'
            order = self.router.place_market_order(symbol, side, quantity)

            if order:
                order_id = order.get('id')
                filled_price = order.get('price', price)
                self.db.update_trade_status(trade_id, 'FILLED', order_id)
                self.position_manager.open_position(symbol, filled_price, quantity, side, trade_id)
                self.position_sizer.increment_positions()
                logger.info(f"✅ Order executed successfully: {order_id}")
            else:
                self.db.update_trade_status(trade_id, 'FAILED')
                logger.error(f"❌ Order execution failed")

        except Exception as e:
            logger.error(f"❌ Error executing signal: {e}", exc_info=True)

    async def run(self):
        """Main run method"""
        self.running = True

        # Initialize
        await self.initialize()

        # Start data poller in background
        self.poller_task = asyncio.create_task(self.poller.run())

        # Start trading loop
        await self.trading_loop()

    def shutdown(self):
        """Graceful shutdown"""
        logger.info("\n🛑 Shutting down ScalperBot...")
        self.running = False

        if self.poller_task:
            self.poller.stop()

        self.db.close()
        logger.info("✅ Shutdown complete")


async def main():
    """Main entry point"""
    bot = ScalperBot()

    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info(f"\n⚠️ Received signal {sig}")
        bot.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await bot.run()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Keyboard interrupt received")
        bot.shutdown()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        bot.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
