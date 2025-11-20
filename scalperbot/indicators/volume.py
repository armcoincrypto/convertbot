"""
Volume Indicators - Z-score and percentile analysis
"""
import pandas as pd
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class VolumeIndicators:
    """
    Calculate volume-based indicators
    - Volume Z-score
    - Volume percentiles
    - Sustained volume detection
    """

    @staticmethod
    def calculate_volume_zscore(
        df: pd.DataFrame,
        lookback: int = 100
    ) -> float:
        """
        Calculate z-score of current volume

        Z-score = (current_volume - mean_volume) / std_volume

        Args:
            df: DataFrame with OHLCV data
            lookback: Number of candles for mean/std calculation

        Returns:
            Z-score of current volume
        """
        if df.empty or len(df) < lookback:
            return np.nan

        volumes = df['volume'].iloc[-lookback:]
        current_volume = volumes.iloc[-1]

        mean_volume = volumes.mean()
        std_volume = volumes.std()

        if std_volume == 0:
            return 0.0

        zscore = (current_volume - mean_volume) / std_volume

        return zscore

    @staticmethod
    def calculate_volume_percentile(
        df: pd.DataFrame,
        percentile: float = 0.95,
        lookback_hours: int = 24
    ) -> Tuple[float, float]:
        """
        Calculate volume percentile threshold

        Args:
            df: DataFrame with 1m OHLCV data
            percentile: Percentile to calculate (0.95 = 95th percentile)
            lookback_hours: Hours to look back (24 = 1 day)

        Returns:
            Tuple of (threshold_volume, current_volume)
        """
        lookback_candles = lookback_hours * 60  # Convert hours to 1m candles

        if df.empty or len(df) < lookback_candles:
            return np.nan, np.nan

        volumes = df['volume'].iloc[-lookback_candles:]
        current_volume = volumes.iloc[-1]

        threshold = volumes.quantile(percentile)

        return threshold, current_volume

    @staticmethod
    def check_volume_surge(
        df: pd.DataFrame,
        zscore_threshold: float = 2.0,
        percentile_threshold: float = 0.90,
        sustained_candles: int = 1,
        lookback_hours: int = 24
    ) -> dict:
        """
        Check if there's a volume surge

        Args:
            df: DataFrame with OHLCV data
            zscore_threshold: Minimum z-score for surge
            percentile_threshold: Minimum percentile (0.90 = 90th percentile)
            sustained_candles: Number of candles volume must stay high
            lookback_hours: Hours for percentile calculation

        Returns:
            Dict with volume surge analysis
        """
        if df.empty:
            return {
                'is_surge': False,
                'zscore': np.nan,
                'percentile_value': np.nan,
                'is_sustained': False,
                'reason': 'No data'
            }

        # Calculate z-score
        zscore = VolumeIndicators.calculate_volume_zscore(df)

        # Calculate percentile
        percentile_vol, current_vol = VolumeIndicators.calculate_volume_percentile(
            df, percentile_threshold, lookback_hours
        )

        if pd.isna(zscore) or pd.isna(percentile_vol):
            return {
                'is_surge': False,
                'zscore': zscore,
                'percentile_value': percentile_vol,
                'current_volume': current_vol,
                'is_sustained': False,
                'reason': 'Insufficient data'
            }

        # Check z-score threshold
        zscore_pass = zscore >= zscore_threshold

        # Check percentile threshold
        percentile_pass = current_vol >= percentile_vol

        # Check if sustained
        is_sustained = True
        if sustained_candles > 1:
            # Check if volume stayed high for N candles
            recent_volumes = df['volume'].iloc[-sustained_candles:]
            sustained_threshold = percentile_vol * 0.8  # Allow 20% drop

            is_sustained = all(v >= sustained_threshold for v in recent_volumes)

        is_surge = zscore_pass and percentile_pass and is_sustained

        return {
            'is_surge': is_surge,
            'zscore': zscore,
            'percentile_value': percentile_vol,
            'current_volume': current_vol,
            'is_sustained': is_sustained,
            'zscore_pass': zscore_pass,
            'percentile_pass': percentile_pass,
            'reason': 'Volume surge detected' if is_surge else 'No volume surge'
        }

    @staticmethod
    def get_average_volume(df: pd.DataFrame, lookback: int = 100) -> float:
        """
        Get average volume over lookback period

        Args:
            df: DataFrame with OHLCV data
            lookback: Number of candles to average

        Returns:
            Average volume
        """
        if df.empty or len(df) < lookback:
            return np.nan

        return df['volume'].iloc[-lookback:].mean()

    @staticmethod
    def get_volume_trend(df: pd.DataFrame, short: int = 20, long: int = 100) -> str:
        """
        Determine if volume is increasing or decreasing

        Args:
            df: DataFrame with OHLCV data
            short: Short-term average period
            long: Long-term average period

        Returns:
            'increasing', 'decreasing', or 'neutral'
        """
        if df.empty or len(df) < long:
            return 'unknown'

        short_avg = df['volume'].iloc[-short:].mean()
        long_avg = df['volume'].iloc[-long:].mean()

        if short_avg > long_avg * 1.2:  # 20% higher
            return 'increasing'
        elif short_avg < long_avg * 0.8:  # 20% lower
            return 'decreasing'
        else:
            return 'neutral'

    @staticmethod
    def calculate_volume_profile(
        df: pd.DataFrame,
        lookback: int = 100
    ) -> dict:
        """
        Calculate comprehensive volume profile

        Returns:
            Dict with volume statistics
        """
        if df.empty or len(df) < lookback:
            return {
                'mean': np.nan,
                'median': np.nan,
                'std': np.nan,
                'p50': np.nan,
                'p75': np.nan,
                'p90': np.nan,
                'p95': np.nan,
                'p99': np.nan
            }

        volumes = df['volume'].iloc[-lookback:]

        return {
            'mean': volumes.mean(),
            'median': volumes.median(),
            'std': volumes.std(),
            'p50': volumes.quantile(0.50),
            'p75': volumes.quantile(0.75),
            'p90': volumes.quantile(0.90),
            'p95': volumes.quantile(0.95),
            'p99': volumes.quantile(0.99)
        }
