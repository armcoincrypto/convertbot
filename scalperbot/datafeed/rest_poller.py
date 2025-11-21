"""
REST API Poller
Polls MEXC market data every N seconds
Feeds data into CandleStore and OrderBook
"""
import asyncio
import time
from typing import List
import logging
from exchanges.adapter import MEXCAdapter
from datafeed.candle_store import CandleStore
from datafeed.orderbook import OrderBook

logger = logging.getLogger(__name__)


class RESTPoller:
    """
    Polls market data from MEXC REST API
    - Fetches OHLCV candles
    - Fetches order book
    - Runs on configurable interval
    """

    def __init__(
        self,
        exchange: MEXCAdapter,
        candle_store: CandleStore,
        orderbook: OrderBook,
        symbols: List[str],
        poll_interval: int = 10
    ):
        self.exchange = exchange
        self.candle_store = candle_store
        self.orderbook = orderbook
        self.symbols = symbols
        self.poll_interval = poll_interval
        self.running = False

        # Track last poll time per symbol
        self.last_poll: dict = {}

    async def initialize_historical(self):
        """Fetch historical candles on startup to speed up warmup"""
        logger.info("🔄 Fetching historical candles for warmup...")
        logger.info("📥 Loading multi-timeframe data for v2.0 strategy...")

        for symbol in self.symbols:
            try:
                # Fetch 1m candles in chunks to build up sufficient history
                # Need 6000+ minutes for 30m EMA200 (200 bars * 30 min)
                # Fetch in multiple chunks since exchanges limit ~1000-1500 per request

                all_candles = []
                chunks_to_fetch = [
                    ('1m', 1000),  # ~16 hours
                    ('1m', 1000),  # Another 16 hours (going back in time)
                    ('1m', 1000),  # Another 16 hours
                    ('1m', 1000),  # Another 16 hours
                    ('1m', 1000),  # Another 16 hours
                    ('1m', 1000),  # Another 16 hours
                    ('1m', 1000),  # Another 16 hours (total ~112 hours = 4.6 days)
                ]

                logger.info(f"📊 {symbol}: Fetching {len(chunks_to_fetch)} chunks of historical data...")

                for i, (timeframe, limit) in enumerate(chunks_to_fetch):
                    try:
                        # Calculate the 'since' timestamp for each chunk
                        # Go back in time: chunk 0 is most recent, chunk 6 is oldest
                        minutes_back = (len(chunks_to_fetch) - i) * limit
                        since_ms = int((time.time() - (minutes_back * 60)) * 1000)

                        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit, since=since_ms)

                        if ohlcv:
                            all_candles.extend(ohlcv)
                            logger.debug(f"  Chunk {i+1}/{len(chunks_to_fetch)}: +{len(ohlcv)} candles")

                        # Delay to avoid rate limits
                        await asyncio.sleep(0.3)

                    except Exception as e:
                        logger.warning(f"⚠️ Failed to fetch chunk {i+1} for {symbol}: {e}")
                        continue

                if all_candles:
                    # Remove duplicates and sort
                    unique_candles = {}
                    for candle in all_candles:
                        timestamp = candle[0]
                        unique_candles[timestamp] = candle

                    sorted_candles = sorted(unique_candles.values(), key=lambda x: x[0])

                    self.candle_store.initialize_historical(symbol, sorted_candles)
                    logger.info(f"✅ {symbol}: Loaded {len(sorted_candles)} historical 1m candles (~{len(sorted_candles)/60:.1f} hours)")
                else:
                    logger.warning(f"⚠️ No historical data for {symbol}")

            except Exception as e:
                logger.error(f"❌ Error fetching historical data for {symbol}: {e}")

            # Small delay between symbols to avoid rate limits
            await asyncio.sleep(0.5)

    async def poll_once(self):
        """Poll all symbols once"""
        for symbol in self.symbols:
            try:
                # Fetch latest OHLCV (1m)
                ohlcv = self.exchange.fetch_ohlcv(symbol, '1m', limit=2)

                if ohlcv:
                    # Add latest candle(s)
                    for candle in ohlcv:
                        timestamp, open_p, high, low, close, volume = candle
                        self.candle_store.add_candle(
                            symbol, timestamp, open_p, high, low, close, volume
                        )

                # Fetch order book
                ob_data = self.exchange.fetch_order_book(symbol, limit=10)

                if ob_data:
                    self.orderbook.update(
                        symbol,
                        ob_data.get('bids', []),
                        ob_data.get('asks', []),
                        ob_data.get('timestamp', int(time.time() * 1000))
                    )

            except Exception as e:
                logger.error(f"❌ Error polling {symbol}: {e}")

    async def run(self):
        """Main polling loop"""
        self.running = True
        logger.info(f"🚀 REST Poller started (interval: {self.poll_interval}s)")

        # Initialize with historical data first
        await self.initialize_historical()

        cycle = 0
        while self.running:
            cycle += 1
            start_time = time.time()

            logger.debug(f"🔄 Poll cycle #{cycle}")

            await self.poll_once()

            # Sleep for remaining time
            elapsed = time.time() - start_time
            sleep_time = max(0, self.poll_interval - elapsed)

            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            else:
                logger.warning(f"⚠️ Poll cycle took {elapsed:.2f}s (longer than {self.poll_interval}s interval)")

    def stop(self):
        """Stop the poller"""
        self.running = False
        logger.info("⏹️ REST Poller stopped")
