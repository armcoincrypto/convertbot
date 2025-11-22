"""
Trend Indicators - EMA calculations for multi-timeframe analysis
"""
import pandas as pd
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TrendIndicators:
    """
    Calculate trend indicators across multiple timeframes
    - EMA (Exponential Moving Average)
    - Trend direction detection
    """

    @staticmethod
    def calculate_ema(df: pd.DataFrame, period: int, column: str = 'close') -> pd.Series:
        """
        Calculate Exponential Moving Average

        Args:
            df: DataFrame with OHLCV data
            period: EMA period (9, 21, 50, 200, etc.)
            column: Column to calculate EMA on (default: close)

        Returns:
            Series with EMA values
        """
        if df.empty or len(df) < period:
            return pd.Series(dtype=float)

        return df[column].ewm(span=period, adjust=False).mean()

    @staticmethod
    def check_ema_bullish(ema_fast: float, ema_slow: float) -> bool:
        """
        Check if fast EMA is above slow EMA (bullish)

        Args:
            ema_fast: Fast EMA value (e.g., EMA9, EMA50)
            ema_slow: Slow EMA value (e.g., EMA21, EMA200)

        Returns:
            True if bullish trend
        """
        if pd.isna(ema_fast) or pd.isna(ema_slow):
            return False

        return ema_fast > ema_slow

    @staticmethod
    def get_trend_strength(ema_fast: float, ema_slow: float) -> float:
        """
        Calculate trend strength as percentage difference between EMAs

        Returns:
            Percentage difference (positive = bullish, negative = bearish)
        """
        if pd.isna(ema_fast) or pd.isna(ema_slow) or ema_slow == 0:
            return 0.0

        return ((ema_fast - ema_slow) / ema_slow) * 100

    @staticmethod
    def calculate_multi_ema(
        df: pd.DataFrame,
        periods: list = [9, 21, 50, 200],
        column: str = 'close'
    ) -> dict:
        """
        Calculate multiple EMAs at once

        Args:
            df: DataFrame with OHLCV data
            periods: List of EMA periods
            column: Column to calculate on

        Returns:
            Dict with {period: latest_ema_value}
        """
        result = {}

        for period in periods:
            ema_series = TrendIndicators.calculate_ema(df, period, column)
            if not ema_series.empty:
                result[f'ema_{period}'] = ema_series.iloc[-1]
            else:
                result[f'ema_{period}'] = np.nan

        return result

    @staticmethod
    def check_30m_trend(df_30m: pd.DataFrame) -> dict:
        """
        Check 30m trend (EMA50 > EMA200 = bullish)

        Args:
            df_30m: DataFrame with 30m candles

        Returns:
            Dict with trend analysis
        """
        if df_30m.empty or len(df_30m) < 200:
            return {
                'bullish': False,
                'reason': 'Insufficient data',
                'ema_50': np.nan,
                'ema_200': np.nan
            }

        ema_50 = TrendIndicators.calculate_ema(df_30m, 50).iloc[-1]
        ema_200 = TrendIndicators.calculate_ema(df_30m, 200).iloc[-1]

        bullish = TrendIndicators.check_ema_bullish(ema_50, ema_200)
        strength = TrendIndicators.get_trend_strength(ema_50, ema_200)

        return {
            'bullish': bullish,
            'ema_50': ema_50,
            'ema_200': ema_200,
            'strength_pct': strength,
            'reason': 'Bullish 30m trend' if bullish else 'Bearish 30m trend'
        }

    @staticmethod
    def check_5m_momentum(df_5m: pd.DataFrame) -> dict:
        """
        Check 5m momentum (EMA9 > EMA21 = bullish)

        Args:
            df_5m: DataFrame with 5m candles

        Returns:
            Dict with momentum analysis
        """
        if df_5m.empty or len(df_5m) < 21:
            return {
                'bullish': False,
                'reason': 'Insufficient data',
                'ema_9': np.nan,
                'ema_21': np.nan
            }

        ema_9 = TrendIndicators.calculate_ema(df_5m, 9).iloc[-1]
        ema_21 = TrendIndicators.calculate_ema(df_5m, 21).iloc[-1]

        bullish = TrendIndicators.check_ema_bullish(ema_9, ema_21)
        strength = TrendIndicators.get_trend_strength(ema_9, ema_21)

        return {
            'bullish': bullish,
            'ema_9': ema_9,
            'ema_21': ema_21,
            'strength_pct': strength,
            'reason': 'Bullish 5m momentum' if bullish else 'Bearish 5m momentum'
        }

    @staticmethod
    def check_multi_timeframe_trend(df_30m: pd.DataFrame, df_5m: pd.DataFrame) -> dict:
        """
        Check multi-timeframe trend alignment
        EITHER 30m OR 5m must be bullish (relaxed for more signals)

        Returns:
            Dict with complete trend analysis
        """
        trend_30m = TrendIndicators.check_30m_trend(df_30m)
        momentum_5m = TrendIndicators.check_5m_momentum(df_5m)

        # Changed from AND to OR - accept if either timeframe is bullish
        aligned = trend_30m['bullish'] or momentum_5m['bullish']

        return {
            'aligned': aligned,
            'trend_30m': trend_30m,
            'momentum_5m': momentum_5m,
            'reason': 'Multi-TF aligned' if aligned else 'Multi-TF not aligned'
        }
