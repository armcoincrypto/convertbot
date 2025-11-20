"""
ScalperBot v2.0 - Pair-Specific Configuration
Optimized thresholds for BTC, ETH, SOL, XRP
"""

# Pair-specific trading parameters
PAIR_CONFIG = {
    'BTC/USDT': {
        # Breakout detection
        'breakout_bps': 8,                    # Base breakout threshold
        'breakout_volatility_adjusted': True, # Increase threshold in high volatility
        'breakout_high_vol_adjustment': 4,    # Add 4 bps when ATR > threshold

        # Volume filters
        'volume_zscore': 1.7,                 # Minimum z-score for volume surge
        'volume_percentile': 0.95,            # 95th percentile
        'sustained_candles': 1,               # Volume must stay high for N candles

        # Volatility (ATR) thresholds
        'atr_normal_range': (7, 18),          # Normal ATR range in bps
        'atr_high_threshold': 20,             # High volatility threshold in bps

        # Dynamic exits (ATR multipliers)
        'atr_sl_multiplier': 1.5,             # Stop loss = ATR × 1.5
        'atr_tp_multiplier': 3.0,             # Take profit = ATR × 3.0
        'atr_trail_multiplier': 1.2,          # Trail distance = ATR × 1.2
        'atr_trail_activation_multiplier': 1.5, # Trail activates at ATR × 1.5

        # Execution limits
        'spread_limit_bps': 6,                # Max acceptable spread
        'max_slippage_bps': 4,                # Max slippage tolerance

        # Expected performance
        'expected_signals_per_day': (2, 4),   # Range of expected signals
        'signal_quality': 'highest',          # Reliability rating
        'fakeout_risk': 'lowest',             # Fakeout probability
    },

    'ETH/USDT': {
        # Breakout detection
        'breakout_bps': 10,
        'breakout_volatility_adjusted': True,
        'breakout_high_vol_adjustment': 5,

        # Volume filters
        'volume_zscore': 2.0,
        'volume_percentile': 0.90,
        'sustained_candles': 1,

        # Volatility (ATR) thresholds
        'atr_normal_range': (10, 25),
        'atr_high_threshold': 30,

        # Dynamic exits (ATR multipliers)
        'atr_sl_multiplier': 1.8,
        'atr_tp_multiplier': 3.5,
        'atr_trail_multiplier': 1.2,
        'atr_trail_activation_multiplier': 1.5,

        # Execution limits
        'spread_limit_bps': 8,
        'max_slippage_bps': 4,

        # Expected performance
        'expected_signals_per_day': (3, 6),
        'signal_quality': 'high',
        'fakeout_risk': 'low',
    },

    'SOL/USDT': {
        # Breakout detection
        'breakout_bps': 12,
        'breakout_volatility_adjusted': True,
        'breakout_high_vol_adjustment': 8,

        # Volume filters
        'volume_zscore': 2.3,
        'volume_percentile': 0.90,
        'sustained_candles': 1,

        # Volatility (ATR) thresholds
        'atr_normal_range': (20, 50),
        'atr_high_threshold': 60,

        # Dynamic exits (ATR multipliers)
        'atr_sl_multiplier': 2.0,
        'atr_tp_multiplier': 4.0,
        'atr_trail_multiplier': 1.3,
        'atr_trail_activation_multiplier': 1.5,

        # Execution limits
        'spread_limit_bps': 12,
        'max_slippage_bps': 4,

        # Expected performance
        'expected_signals_per_day': (5, 10),
        'signal_quality': 'medium',
        'fakeout_risk': 'medium',
    },

    'XRP/USDT': {
        # Breakout detection
        'breakout_bps': 6,
        'breakout_volatility_adjusted': False,  # XRP doesn't need volatility adjustment
        'breakout_high_vol_adjustment': 3,

        # Volume filters
        'volume_zscore': 1.5,
        'volume_percentile': 0.85,
        'sustained_candles': 2,  # XRP requires 2 candles of sustained volume

        # Volatility (ATR) thresholds
        'atr_normal_range': (5, 12),
        'atr_high_threshold': 15,

        # Dynamic exits (ATR multipliers)
        'atr_sl_multiplier': 2.2,
        'atr_tp_multiplier': 3.2,
        'atr_trail_multiplier': 1.4,
        'atr_trail_activation_multiplier': 1.6,

        # Execution limits
        'spread_limit_bps': 10,
        'max_slippage_bps': 4,

        # Expected performance
        'expected_signals_per_day': (1, 3),
        'signal_quality': 'medium',
        'fakeout_risk': 'high',  # Many false signals, strict filtering required
    },
}


# Global strategy parameters
STRATEGY_CONFIG = {
    # Multi-timeframe requirements
    '30m_trend_required': True,       # EMA50 > EMA200 on 30m
    '5m_momentum_required': True,     # EMA9 > EMA21 on 5m

    # Bollinger Band squeeze parameters
    'bb_period': 20,
    'bb_std_dev': 2.0,
    'bb_squeeze_percentile': 0.30,    # Bottom 30% of BB width
    'bb_expansion_threshold': 0.20,   # 20% expansion required
    'bb_expansion_lookback': 4,       # Check expansion over 4 candles
    'bb_lookback_candles': 2880,      # 48 hours for percentile calculation

    # Volume analysis parameters
    'volume_lookback_hours': 24,      # 24 hours for percentile
    'volume_zscore_lookback': 100,    # 100 candles for z-score

    # Breakout parameters
    'breakout_lookback_period': 10,   # 10-period high for breakout

    # Time stop
    'time_stop_seconds': 120,         # Exit if not profitable after 2 minutes
    'time_stop_min_profit_bps': 10,   # Minimum profit to avoid time stop

    # Position management
    'max_positions': 3,
    'cooldown_after_loss_seconds': 300,  # 5 min cooldown after loss

    # Risk management
    'risk_pct_per_trade': 0.008,      # 0.8% risk per trade
    'max_position_pct': 0.25,         # Max 25% of equity per position
    'max_notional_usd': 3000,         # Max $3000 per position
    'max_liquidity_cap_usd': 25000,   # Max $25000 position size

    # Stop loss constraints (min/max in bps)
    'sl_min_bps': 12,
    'sl_max_bps': 30,

    # Take profit constraints (min/max in bps)
    'tp_min_bps': 20,
    'tp_max_bps': 60,

    # Trailing stop constraints (min/max in bps)
    'trail_min_bps': 10,
    'trail_max_bps': 20,
    'trail_activation_min_bps': 15,
    'trail_activation_max_bps': 25,
}


def get_pair_config(symbol: str) -> dict:
    """
    Get configuration for a trading pair

    Args:
        symbol: Trading pair (e.g., 'BTC/USDT')

    Returns:
        Dict with pair-specific configuration
    """
    if symbol not in PAIR_CONFIG:
        raise ValueError(f"No configuration found for {symbol}")

    return PAIR_CONFIG[symbol]


def get_all_configured_pairs() -> list:
    """Get list of all configured trading pairs"""
    return list(PAIR_CONFIG.keys())


def is_pair_configured(symbol: str) -> bool:
    """Check if a pair has configuration"""
    return symbol in PAIR_CONFIG
