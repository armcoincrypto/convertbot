"""
Advanced Position Sizer v2.0
Dynamic position sizing based on ATR and risk percentage
"""
import logging
from typing import Dict
import numpy as np

from strategies.scalper_v2_config import STRATEGY_CONFIG

logger = logging.getLogger(__name__)


class PositionSizerV2:
    """
    Advanced position sizer with ATR-based dynamic sizing
    """

    def __init__(self):
        self.config = STRATEGY_CONFIG
        self.open_positions = 0
        self.max_positions = self.config['max_positions']

    def calculate_size(
        self,
        symbol: str,
        entry_price: float,
        equity_usd: float,
        atr_bps: float,
        sl_bps: float
    ) -> Dict[str, any]:
        """
        Calculate position size based on risk and ATR

        Args:
            symbol: Trading pair
            entry_price: Entry price
            equity_usd: Total account equity
            atr_bps: Current ATR in basis points
            sl_bps: Stop loss distance in basis points

        Returns:
            Dict with position size details
        """
        # Validate inputs
        if equity_usd <= 0:
            return {
                'can_trade': False,
                'reason': 'Zero or negative equity',
                'quantity': 0,
                'notional_usd': 0
            }

        if np.isnan(atr_bps) or sl_bps <= 0:
            return {
                'can_trade': False,
                'reason': 'Invalid ATR or SL',
                'quantity': 0,
                'notional_usd': 0
            }

        # Check max positions
        if self.open_positions >= self.max_positions:
            return {
                'can_trade': False,
                'reason': f'Max positions reached ({self.open_positions}/{self.max_positions})',
                'quantity': 0,
                'notional_usd': 0
            }

        # Calculate risk amount (0.8% of equity per trade)
        risk_pct = self.config['risk_pct_per_trade']
        risk_usd = equity_usd * risk_pct

        # Calculate position size based on risk and stop loss
        # Position size = Risk Amount / (SL distance in decimal)
        sl_decimal = sl_bps / 10000
        position_usd_risk_based = risk_usd / sl_decimal

        # Apply maximum position percentage (25% of equity)
        max_position_pct = self.config['max_position_pct']
        max_position_usd_pct = equity_usd * max_position_pct

        # Apply hard caps
        max_notional = self.config['max_notional_usd']
        max_liquidity_cap = self.config['max_liquidity_cap_usd']

        # Take minimum of all constraints
        position_usd = min(
            position_usd_risk_based,
            max_position_usd_pct,
            max_notional,
            max_liquidity_cap
        )

        # Convert to quantity
        quantity = position_usd / entry_price

        # Minimum position size ($10)
        if position_usd < 10:
            return {
                'can_trade': False,
                'reason': f'Position too small: ${position_usd:.2f} < $10',
                'quantity': 0,
                'notional_usd': position_usd
            }

        # Calculate which constraint was limiting
        if position_usd == position_usd_risk_based:
            limiting_factor = 'risk_based'
        elif position_usd == max_position_usd_pct:
            limiting_factor = 'max_pct'
        elif position_usd == max_notional:
            limiting_factor = 'max_notional'
        else:
            limiting_factor = 'liquidity_cap'

        return {
            'can_trade': True,
            'quantity': quantity,
            'notional_usd': position_usd,
            'risk_usd': risk_usd,
            'risk_pct': risk_pct * 100,
            'sl_bps': sl_bps,
            'atr_bps': atr_bps,
            'limiting_factor': limiting_factor,
            'position_pct_of_equity': (position_usd / equity_usd) * 100
        }

    def increment_positions(self):
        """Increment open position count"""
        self.open_positions += 1
        logger.debug(f"Open positions: {self.open_positions}/{self.max_positions}")

    def decrement_positions(self):
        """Decrement open position count"""
        if self.open_positions > 0:
            self.open_positions -= 1
        logger.debug(f"Open positions: {self.open_positions}/{self.max_positions}")

    def get_position_count(self) -> int:
        """Get current open position count"""
        return self.open_positions

    def can_open_new_position(self) -> bool:
        """Check if we can open a new position"""
        return self.open_positions < self.max_positions

    def log_size_calculation(self, sizing: Dict[str, any], symbol: str):
        """
        Log position sizing details

        Args:
            sizing: Sizing dict from calculate_size()
            symbol: Trading pair
        """
        if not sizing['can_trade']:
            logger.warning(f"⚠️ {symbol} - Cannot trade: {sizing['reason']}")
            return

        logger.info(f"\n💰 Position Sizing for {symbol}:")
        logger.info(f"  Quantity: {sizing['quantity']:.6f}")
        logger.info(f"  Notional: ${sizing['notional_usd']:.2f}")
        logger.info(f"  Risk: ${sizing['risk_usd']:.2f} ({sizing['risk_pct']:.2f}%)")
        logger.info(f"  Stop Loss: {sizing['sl_bps']:.1f} bps")
        logger.info(f"  Position %: {sizing['position_pct_of_equity']:.1f}% of equity")
        logger.info(f"  Limiting Factor: {sizing['limiting_factor']}")
        logger.info(f"  Open Positions: {self.open_positions}/{self.max_positions}")
