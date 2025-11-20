"""
ScalperBot v2.0 - Professional Multi-Pair Scalping Strategy

4-Filter Entry System:
1. Multi-timeframe trend (30m + 5m)
2. Bollinger Band squeeze → expansion
3. Volume surge (z-score + percentile)
4. Breakout confirmation (pair-specific)
"""
import logging
import time
from typing import Optional, List, Dict
import pandas as pd

from datafeed.candle_store import CandleStore
from indicators.trend import TrendIndicators
from indicators.volatility import VolatilityIndicators
from indicators.volume import VolumeIndicators
from strategies.scalper_v2_config import (
    get_pair_config,
    get_all_configured_pairs,
    STRATEGY_CONFIG,
    is_pair_configured
)

logger = logging.getLogger(__name__)


class ScalperV2Strategy:
    """
    Professional scalping strategy with multi-timeframe analysis
    and pair-specific optimizations
    """

    def __init__(self, candle_store: CandleStore):
        self.candle_store = candle_store
        self.config = STRATEGY_CONFIG

        logger.info("🚀 ScalperBot v2.0 Strategy initialized")
        logger.info(f"   30m trend filter: {'Enabled' if self.config['30m_trend_required'] else 'Disabled'}")
        logger.info(f"   5m momentum filter: {'Enabled' if self.config['5m_momentum_required'] else 'Disabled'}")
        logger.info(f"   BB squeeze percentile: {self.config['bb_squeeze_percentile']*100:.0f}%")
        logger.info(f"   Max positions: {self.config['max_positions']}")

    def check_filter_1_trend(self, symbol: str) -> dict:
        """
        Filter 1: Multi-Timeframe Trend
        - 30m: EMA50 > EMA200 (bullish trend)
        - 5m: EMA9 > EMA21 (bullish momentum)
        """
        # Get 30m candles
        df_30m = self.candle_store.get_candles(symbol, '30m', limit=250)
        if df_30m.empty or len(df_30m) < 200:
            return {
                'passed': False,
                'reason': 'Insufficient 30m data',
                'details': {}
            }

        # Get 5m candles
        df_5m = self.candle_store.get_candles(symbol, '5m', limit=100)
        if df_5m.empty or len(df_5m) < 21:
            return {
                'passed': False,
                'reason': 'Insufficient 5m data',
                'details': {}
            }

        # Check multi-timeframe trend
        trend_analysis = TrendIndicators.check_multi_timeframe_trend(df_30m, df_5m)

        return {
            'passed': trend_analysis['aligned'],
            'reason': trend_analysis['reason'],
            'details': {
                '30m_trend': trend_analysis['trend_30m'],
                '5m_momentum': trend_analysis['momentum_5m']
            }
        }

    def check_filter_2_squeeze(self, symbol: str) -> dict:
        """
        Filter 2: Bollinger Band Squeeze → Expansion
        - BB width in bottom 30% of last 48 hours
        - BB width expanding by >20% in last 3-4 candles
        """
        df_1m = self.candle_store.get_candles(symbol, '1m')

        if df_1m.empty or len(df_1m) < self.config['bb_lookback_candles']:
            return {
                'passed': False,
                'reason': 'Insufficient 1m data for BB squeeze',
                'details': {}
            }

        squeeze_analysis = VolatilityIndicators.check_bb_squeeze(
            df_1m,
            lookback_candles=self.config['bb_lookback_candles'],
            squeeze_threshold=self.config['bb_squeeze_percentile'],
            expansion_threshold=self.config['bb_expansion_threshold'],
            expansion_lookback=self.config['bb_expansion_lookback']
        )

        passed = squeeze_analysis['is_squeeze'] and squeeze_analysis['is_expanding']

        return {
            'passed': passed,
            'reason': squeeze_analysis['reason'],
            'details': squeeze_analysis
        }

    def check_filter_3_volume(self, symbol: str) -> dict:
        """
        Filter 3: Volume Surge
        - Z-score above pair-specific threshold
        - Volume above percentile threshold
        - Sustained for N candles (pair-specific)
        """
        pair_config = get_pair_config(symbol)

        df_1m = self.candle_store.get_candles(symbol, '1m')

        if df_1m.empty:
            return {
                'passed': False,
                'reason': 'No 1m data for volume check',
                'details': {}
            }

        volume_analysis = VolumeIndicators.check_volume_surge(
            df_1m,
            zscore_threshold=pair_config['volume_zscore'],
            percentile_threshold=pair_config['volume_percentile'],
            sustained_candles=pair_config['sustained_candles'],
            lookback_hours=self.config['volume_lookback_hours']
        )

        return {
            'passed': volume_analysis['is_surge'],
            'reason': volume_analysis['reason'],
            'details': volume_analysis
        }

    def check_filter_4_breakout(self, symbol: str, current_price: float) -> dict:
        """
        Filter 4: Breakout Confirmation
        - Price closes above 10-period high
        - Breakout threshold is pair-specific
        - Threshold increases in high volatility
        """
        pair_config = get_pair_config(symbol)

        df_1m = self.candle_store.get_candles(symbol, '1m')

        if df_1m.empty or len(df_1m) < self.config['breakout_lookback_period']:
            return {
                'passed': False,
                'reason': 'Insufficient data for breakout check',
                'details': {}
            }

        # Get 10-period high
        recent_highs = df_1m['high'].iloc[-self.config['breakout_lookback_period']:]
        high_10m = recent_highs.max()

        # Get current ATR for volatility adjustment
        atr_bps = VolatilityIndicators.calculate_atr_bps(df_1m, period=14)

        # Base breakout threshold
        breakout_threshold_bps = pair_config['breakout_bps']

        # Adjust for high volatility
        if pair_config['breakout_volatility_adjusted'] and not pd.isna(atr_bps):
            if atr_bps > pair_config['atr_high_threshold']:
                adjustment = pair_config['breakout_high_vol_adjustment']
                breakout_threshold_bps += adjustment
                volatility_adjusted = True
            else:
                volatility_adjusted = False
        else:
            volatility_adjusted = False

        # Calculate required breakout price
        required_price = high_10m * (1 + breakout_threshold_bps / 10000)

        # Check if current price breaks out
        is_breakout = current_price >= required_price

        return {
            'passed': is_breakout,
            'reason': f'Breakout: {is_breakout}',
            'details': {
                'current_price': current_price,
                'high_10m': high_10m,
                'required_price': required_price,
                'breakout_threshold_bps': breakout_threshold_bps,
                'volatility_adjusted': volatility_adjusted,
                'atr_bps': atr_bps
            }
        }

    def generate_signal(self, symbol: str) -> Optional[dict]:
        """
        Generate entry signal for a symbol
        All 4 filters must pass
        """
        if not is_pair_configured(symbol):
            logger.warning(f"⚠️ {symbol} is not configured for v2.0 strategy")
            return None

        logger.info(f"\n{'='*60}")
        logger.info(f"📊 {symbol} Strategy v2.0 Check:")

        # Get current price
        current_price = self.candle_store.get_latest_price(symbol)
        if not current_price:
            logger.warning(f"⚠️ {symbol} - No current price available")
            return None

        # Get current ATR (needed for exits)
        df_1m = self.candle_store.get_candles(symbol, '1m')
        atr_bps = VolatilityIndicators.calculate_atr_bps(df_1m, period=14)

        # Filter 1: Multi-timeframe trend
        filter_1 = self.check_filter_1_trend(symbol)
        logger.info(f"  Filter 1 (Trend): {filter_1['reason']} {'✅' if filter_1['passed'] else '❌'}")

        if not filter_1['passed']:
            logger.info(f"❌ {symbol} - Filter 1 failed")
            logger.info(f"{'='*60}\n")
            return None

        # Filter 2: BB squeeze → expansion
        filter_2 = self.check_filter_2_squeeze(symbol)
        logger.info(f"  Filter 2 (Squeeze): {filter_2['reason']} {'✅' if filter_2['passed'] else '❌'}")

        if not filter_2['passed']:
            logger.info(f"❌ {symbol} - Filter 2 failed")
            logger.info(f"{'='*60}\n")
            return None

        # Filter 3: Volume surge
        filter_3 = self.check_filter_3_volume(symbol)
        vol_details = filter_3['details']
        logger.info(f"  Filter 3 (Volume): z={vol_details.get('zscore', 0):.1f}, "
                   f"sustained={vol_details.get('is_sustained', False)} {'✅' if filter_3['passed'] else '❌'}")

        if not filter_3['passed']:
            logger.info(f"❌ {symbol} - Filter 3 failed")
            logger.info(f"{'='*60}\n")
            return None

        # Filter 4: Breakout
        filter_4 = self.check_filter_4_breakout(symbol, current_price)
        bo_details = filter_4['details']
        logger.info(f"  Filter 4 (Breakout): price={current_price:.4f}, "
                   f"required={bo_details.get('required_price', 0):.4f}, "
                   f"threshold={bo_details.get('breakout_threshold_bps', 0):.1f}bps {'✅' if filter_4['passed'] else '❌'}")

        if not filter_4['passed']:
            logger.info(f"❌ {symbol} - Filter 4 failed")
            logger.info(f"{'='*60}\n")
            return None

        # All filters passed!
        logger.info(f"✅ {symbol} - ALL 4 FILTERS PASSED - ENTRY SIGNAL GENERATED")
        logger.info(f"{'='*60}\n")

        # Build signal
        signal = {
            'symbol': symbol,
            'action': 'BUY',
            'price': current_price,
            'timestamp': time.time(),
            'strategy': 'ScalperV2',
            'atr_bps': atr_bps,
            'filters': {
                'trend': filter_1,
                'squeeze': filter_2,
                'volume': filter_3,
                'breakout': filter_4
            },
            'reason': f'All 4 filters passed: Trend aligned, BB expanding, Volume surge (z={vol_details.get("zscore", 0):.1f}), Breakout confirmed'
        }

        return signal

    def run_for_all_symbols(self, symbols: List[str]) -> List[dict]:
        """
        Run strategy for all configured symbols

        Args:
            symbols: List of trading pairs

        Returns:
            List of entry signals
        """
        signals = []

        for symbol in symbols:
            try:
                signal = self.generate_signal(symbol)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.error(f"❌ Error running strategy for {symbol}: {e}", exc_info=True)

        return signals

    def get_strategy_info(self) -> dict:
        """Get strategy information"""
        return {
            'name': 'ScalperBot v2.0',
            'version': '2.0.0',
            'description': 'Professional multi-pair scalping with 4-filter system',
            'filters': [
                '1. Multi-timeframe trend (30m + 5m)',
                '2. Bollinger Band squeeze → expansion',
                '3. Volume surge (z-score + percentile)',
                '4. Breakout confirmation (pair-specific)'
            ],
            'configured_pairs': list(get_all_configured_pairs()),
            'config': self.config
        }
