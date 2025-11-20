"""
Dynamic Stop Loss and Take Profit Calculator
ATR-based exits with pair-specific multipliers
"""
import logging
from typing import Dict, Optional
import numpy as np

from strategies.scalper_v2_config import get_pair_config, STRATEGY_CONFIG

logger = logging.getLogger(__name__)


class DynamicStops:
    """
    Calculate dynamic stop loss and take profit levels
    based on ATR and pair-specific multipliers
    """

    def __init__(self):
        self.config = STRATEGY_CONFIG

    def calculate_stop_loss(
        self,
        symbol: str,
        entry_price: float,
        atr_bps: float
    ) -> Dict[str, float]:
        """
        Calculate dynamic stop loss based on ATR

        Args:
            symbol: Trading pair
            entry_price: Entry price
            atr_bps: Current ATR in basis points

        Returns:
            Dict with stop loss details
        """
        if np.isnan(atr_bps):
            # Fallback to default if ATR not available
            atr_bps = 15.0  # Conservative default

        pair_config = get_pair_config(symbol)

        # Calculate SL distance using pair-specific multiplier
        sl_bps = atr_bps * pair_config['atr_sl_multiplier']

        # Apply floor and ceiling constraints
        sl_bps = max(self.config['sl_min_bps'], min(sl_bps, self.config['sl_max_bps']))

        # Calculate SL price
        sl_price = entry_price * (1 - sl_bps / 10000)

        return {
            'sl_price': sl_price,
            'sl_bps': sl_bps,
            'atr_bps': atr_bps,
            'multiplier': pair_config['atr_sl_multiplier'],
            'distance_usd': entry_price - sl_price
        }

    def calculate_take_profit(
        self,
        symbol: str,
        entry_price: float,
        atr_bps: float
    ) -> Dict[str, float]:
        """
        Calculate dynamic take profit based on ATR

        Args:
            symbol: Trading pair
            entry_price: Entry price
            atr_bps: Current ATR in basis points

        Returns:
            Dict with take profit details
        """
        if np.isnan(atr_bps):
            atr_bps = 15.0  # Conservative default

        pair_config = get_pair_config(symbol)

        # Calculate TP distance using pair-specific multiplier
        tp_bps = atr_bps * pair_config['atr_tp_multiplier']

        # Apply floor and ceiling constraints
        tp_bps = max(self.config['tp_min_bps'], min(tp_bps, self.config['tp_max_bps']))

        # Calculate TP price
        tp_price = entry_price * (1 + tp_bps / 10000)

        return {
            'tp_price': tp_price,
            'tp_bps': tp_bps,
            'atr_bps': atr_bps,
            'multiplier': pair_config['atr_tp_multiplier'],
            'distance_usd': tp_price - entry_price,
            'risk_reward': tp_bps / (atr_bps * pair_config['atr_sl_multiplier']) if atr_bps > 0 else 0
        }

    def calculate_trailing_stop(
        self,
        symbol: str,
        entry_price: float,
        atr_bps: float
    ) -> Dict[str, float]:
        """
        Calculate trailing stop parameters

        Args:
            symbol: Trading pair
            entry_price: Entry price
            atr_bps: Current ATR in basis points

        Returns:
            Dict with trailing stop configuration
        """
        if np.isnan(atr_bps):
            atr_bps = 15.0

        pair_config = get_pair_config(symbol)

        # Activation threshold (profit before trailing starts)
        activation_bps = atr_bps * pair_config['atr_trail_activation_multiplier']
        activation_bps = max(
            self.config['trail_activation_min_bps'],
            min(activation_bps, self.config['trail_activation_max_bps'])
        )
        activation_price = entry_price * (1 + activation_bps / 10000)

        # Trail distance (how far below highest price)
        trail_bps = atr_bps * pair_config['atr_trail_multiplier']
        trail_bps = max(
            self.config['trail_min_bps'],
            min(trail_bps, self.config['trail_max_bps'])
        )

        return {
            'activation_price': activation_price,
            'activation_bps': activation_bps,
            'trail_bps': trail_bps,
            'atr_bps': atr_bps,
            'activation_multiplier': pair_config['atr_trail_activation_multiplier'],
            'trail_multiplier': pair_config['atr_trail_multiplier']
        }

    def calculate_all_exits(
        self,
        symbol: str,
        entry_price: float,
        atr_bps: float
    ) -> Dict[str, any]:
        """
        Calculate all exit parameters at once

        Args:
            symbol: Trading pair
            entry_price: Entry price
            atr_bps: Current ATR in basis points

        Returns:
            Dict with complete exit configuration
        """
        sl = self.calculate_stop_loss(symbol, entry_price, atr_bps)
        tp = self.calculate_take_profit(symbol, entry_price, atr_bps)
        trail = self.calculate_trailing_stop(symbol, entry_price, atr_bps)

        return {
            'entry_price': entry_price,
            'symbol': symbol,
            'atr_bps': atr_bps,
            'stop_loss': sl,
            'take_profit': tp,
            'trailing_stop': trail,
            'time_stop_seconds': self.config['time_stop_seconds'],
            'time_stop_min_profit_bps': self.config['time_stop_min_profit_bps']
        }

    def log_exit_plan(self, exits: Dict[str, any]):
        """
        Log the exit plan for a position

        Args:
            exits: Exit configuration from calculate_all_exits()
        """
        symbol = exits['symbol']
        entry = exits['entry_price']
        sl = exits['stop_loss']
        tp = exits['take_profit']
        trail = exits['trailing_stop']

        logger.info(f"\n📊 Exit Plan for {symbol}:")
        logger.info(f"  Entry: ${entry:.4f}")
        logger.info(f"  Stop Loss: ${sl['sl_price']:.4f} (-{sl['sl_bps']:.1f} bps)")
        logger.info(f"  Take Profit: ${tp['tp_price']:.4f} (+{tp['tp_bps']:.1f} bps)")
        logger.info(f"  Risk:Reward = 1:{tp['risk_reward']:.2f}")
        logger.info(f"  Trailing: Activates @ ${trail['activation_price']:.4f} (+{trail['activation_bps']:.1f} bps)")
        logger.info(f"  Trail Distance: {trail['trail_bps']:.1f} bps from high")
        logger.info(f"  Time Stop: {exits['time_stop_seconds']}s if PnL < {exits['time_stop_min_profit_bps']} bps")


class ExitChecker:
    """
    Check exit conditions for open positions
    Priority: SL > TP > Trail > Time
    """

    @staticmethod
    def check_stop_loss(
        current_price: float,
        sl_price: float
    ) -> bool:
        """Check if stop loss hit"""
        return current_price <= sl_price

    @staticmethod
    def check_take_profit(
        current_price: float,
        tp_price: float
    ) -> bool:
        """Check if take profit hit"""
        return current_price >= tp_price

    @staticmethod
    def check_trailing_stop(
        current_price: float,
        highest_price: float,
        trail_activation_price: float,
        trail_bps: float
    ) -> Optional[str]:
        """
        Check if trailing stop hit

        Returns:
            Exit reason if hit, None otherwise
        """
        # Check if trail is activated
        if highest_price < trail_activation_price:
            return None  # Not activated yet

        # Calculate drawdown from highest price
        drawdown_bps = ((highest_price - current_price) / highest_price) * 10000

        if drawdown_bps >= trail_bps:
            return f"Trailing stop (high: ${highest_price:.4f}, draw: {drawdown_bps:.1f}bps)"

        return None

    @staticmethod
    def check_time_stop(
        entry_time: float,
        current_time: float,
        time_stop_seconds: int,
        current_pnl_bps: float,
        min_profit_bps: float
    ) -> Optional[str]:
        """
        Check if time stop hit

        Returns:
            Exit reason if hit, None otherwise
        """
        time_in_position = current_time - entry_time

        if time_in_position > time_stop_seconds:
            if current_pnl_bps < min_profit_bps:
                return f"Time stop ({time_in_position:.0f}s, PnL: {current_pnl_bps:+.1f}bps)"

        return None

    @staticmethod
    def check_all_exits(
        current_price: float,
        entry_price: float,
        sl_price: float,
        tp_price: float,
        highest_price: float,
        trail_activation_price: float,
        trail_bps: float,
        entry_time: float,
        current_time: float,
        time_stop_seconds: int,
        min_profit_bps: float
    ) -> Optional[str]:
        """
        Check all exit conditions in priority order

        Args:
            current_price: Current market price
            entry_price: Position entry price
            sl_price: Stop loss price
            tp_price: Take profit price
            highest_price: Highest price reached
            trail_activation_price: Price where trailing activates
            trail_bps: Trailing stop distance in bps
            entry_time: Position entry timestamp
            current_time: Current timestamp
            time_stop_seconds: Time stop duration
            min_profit_bps: Minimum profit to avoid time stop

        Returns:
            Exit reason string if should exit, None otherwise
        """
        # Priority 1: Stop Loss
        if ExitChecker.check_stop_loss(current_price, sl_price):
            return "Stop Loss"

        # Priority 2: Take Profit
        if ExitChecker.check_take_profit(current_price, tp_price):
            return "Take Profit"

        # Priority 3: Trailing Stop
        trail_reason = ExitChecker.check_trailing_stop(
            current_price, highest_price, trail_activation_price, trail_bps
        )
        if trail_reason:
            return trail_reason

        # Priority 4: Time Stop
        current_pnl_bps = ((current_price - entry_price) / entry_price) * 10000
        time_reason = ExitChecker.check_time_stop(
            entry_time, current_time, time_stop_seconds, current_pnl_bps, min_profit_bps
        )
        if time_reason:
            return time_reason

        return None
