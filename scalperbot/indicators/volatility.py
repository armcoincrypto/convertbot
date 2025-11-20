"""
Volatility Indicators - ATR and Bollinger Bands
"""
import pandas as pd
import numpy as np
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class VolatilityIndicators:
    """
    Calculate volatility indicators
    - ATR (Average True Range) in basis points
    - Bollinger Bands
    - BB Width and percentile tracking
    """

    @staticmethod
    def calculate_true_range(df: pd.DataFrame) -> pd.Series:
        """
        Calculate True Range for ATR

        TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
        """
        if df.empty or len(df) < 2:
            return pd.Series(dtype=float)

        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

        return true_range

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR)

        Args:
            df: DataFrame with OHLCV data
            period: ATR period (default 14)

        Returns:
            Series with ATR values
        """
        if df.empty or len(df) < period:
            return pd.Series(dtype=float)

        true_range = VolatilityIndicators.calculate_true_range(df)

        # Calculate ATR as EMA of True Range
        atr = true_range.ewm(span=period, adjust=False).mean()

        return atr

    @staticmethod
    def calculate_atr_bps(df: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate current ATR in basis points

        Args:
            df: DataFrame with OHLCV data
            period: ATR period

        Returns:
            ATR in basis points (e.g., 15.5 bps)
        """
        if df.empty or len(df) < period:
            return np.nan

        atr_series = VolatilityIndicators.calculate_atr(df, period)
        if atr_series.empty:
            return np.nan

        current_atr = atr_series.iloc[-1]
        current_price = df.iloc[-1]['close']

        if current_price == 0:
            return np.nan

        # Convert to basis points (1 bp = 0.01%)
        atr_bps = (current_atr / current_price) * 10000

        return atr_bps

    @staticmethod
    def calculate_bollinger_bands(
        df: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0
    ) -> dict:
        """
        Calculate Bollinger Bands

        Args:
            df: DataFrame with OHLCV data
            period: BB period (default 20)
            std_dev: Standard deviation multiplier (default 2.0)

        Returns:
            Dict with upper, middle, lower bands and current width
        """
        if df.empty or len(df) < period:
            return {
                'upper': np.nan,
                'middle': np.nan,
                'lower': np.nan,
                'width': np.nan,
                'width_pct': np.nan
            }

        # Middle band = SMA
        middle = df['close'].rolling(window=period).mean()

        # Standard deviation
        std = df['close'].rolling(window=period).std()

        # Upper and lower bands
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        # Band width (distance between upper and lower)
        width = upper - lower

        # Width as percentage of price
        width_pct = (width / middle) * 100

        return {
            'upper': upper.iloc[-1] if not upper.empty else np.nan,
            'middle': middle.iloc[-1] if not middle.empty else np.nan,
            'lower': lower.iloc[-1] if not lower.empty else np.nan,
            'width': width.iloc[-1] if not width.empty else np.nan,
            'width_pct': width_pct.iloc[-1] if not width_pct.empty else np.nan,
            'upper_series': upper,
            'middle_series': middle,
            'lower_series': lower,
            'width_series': width
        }

    @staticmethod
    def calculate_bb_width_percentile(
        df: pd.DataFrame,
        lookback_candles: int = 2880,  # 48 hours of 1m candles
        period: int = 20,
        std_dev: float = 2.0
    ) -> float:
        """
        Calculate BB width percentile rank

        Args:
            df: DataFrame with OHLCV data
            lookback_candles: Number of candles to look back for percentile
            period: BB period
            std_dev: Standard deviation multiplier

        Returns:
            Percentile rank (0.0 to 1.0) where 0.30 means bottom 30%
        """
        if df.empty or len(df) < max(period, lookback_candles):
            return np.nan

        # Calculate BB for all candles
        bb = VolatilityIndicators.calculate_bollinger_bands(df, period, std_dev)
        width_series = bb['width_series']

        if width_series.empty or len(width_series) < lookback_candles:
            return np.nan

        # Get last N candles worth of width
        recent_widths = width_series.iloc[-lookback_candles:]
        current_width = width_series.iloc[-1]

        # Calculate percentile rank
        percentile = (recent_widths < current_width).sum() / len(recent_widths)

        return percentile

    @staticmethod
    def check_bb_squeeze(
        df: pd.DataFrame,
        lookback_candles: int = 2880,
        squeeze_threshold: float = 0.30,
        expansion_threshold: float = 0.20,
        expansion_lookback: int = 4
    ) -> dict:
        """
        Check if BB is in squeeze and expanding

        Args:
            df: DataFrame with OHLCV data
            lookback_candles: Lookback for percentile calculation
            squeeze_threshold: BB width must be below this percentile (0.30 = bottom 30%)
            expansion_threshold: BB width must expand by this % (0.20 = 20%)
            expansion_lookback: Number of candles to check expansion

        Returns:
            Dict with squeeze analysis
        """
        if df.empty or len(df) < lookback_candles:
            return {
                'is_squeeze': False,
                'is_expanding': False,
                'percentile': np.nan,
                'expansion_pct': np.nan,
                'reason': 'Insufficient data'
            }

        # Calculate BB width percentile
        percentile = VolatilityIndicators.calculate_bb_width_percentile(df, lookback_candles)

        if pd.isna(percentile):
            return {
                'is_squeeze': False,
                'is_expanding': False,
                'percentile': np.nan,
                'expansion_pct': np.nan,
                'reason': 'Failed to calculate percentile'
            }

        # Check if in squeeze (bottom 30% of width)
        is_squeeze = percentile <= squeeze_threshold

        # Calculate expansion
        bb = VolatilityIndicators.calculate_bollinger_bands(df)
        width_series = bb['width_series']

        if len(width_series) < expansion_lookback:
            return {
                'is_squeeze': is_squeeze,
                'is_expanding': False,
                'percentile': percentile,
                'expansion_pct': np.nan,
                'reason': 'Insufficient data for expansion'
            }

        current_width = width_series.iloc[-1]
        previous_width = width_series.iloc[-expansion_lookback]

        if previous_width == 0:
            expansion_pct = 0
        else:
            expansion_pct = (current_width - previous_width) / previous_width

        is_expanding = expansion_pct >= expansion_threshold

        return {
            'is_squeeze': is_squeeze,
            'is_expanding': is_expanding,
            'percentile': percentile,
            'expansion_pct': expansion_pct * 100,  # Convert to percentage
            'current_width': current_width,
            'previous_width': previous_width,
            'reason': f'Squeeze: {is_squeeze}, Expanding: {is_expanding}'
        }

    @staticmethod
    def is_high_volatility(atr_bps: float, pair: str, thresholds: dict) -> bool:
        """
        Check if volatility is high for the pair

        Args:
            atr_bps: Current ATR in bps
            pair: Trading pair
            thresholds: Dict with pair-specific volatility thresholds

        Returns:
            True if volatility is high
        """
        if pd.isna(atr_bps) or pair not in thresholds:
            return False

        high_threshold = thresholds[pair].get('atr_high_threshold', 999)

        return atr_bps > high_threshold
