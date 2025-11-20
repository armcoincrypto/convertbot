"""
Position Manager - Tracks open positions and manages exits
Implements: Trailing stop, Time stop, Cooldown after losses
"""
import time
from typing import Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Represents an open position"""
    symbol: str
    entry_price: float
    entry_time: float
    quantity: float
    side: str  # 'buy' or 'sell'
    highest_price: float  # For trailing stop
    trade_id: int


class PositionManager:
    """Manages open positions and exit logic"""

    def __init__(self, config):
        self.config = config
        self.positions: Dict[str, Position] = {}
        self.last_loss_time: Dict[str, float] = {}

    def open_position(
        self,
        symbol: str,
        entry_price: float,
        quantity: float,
        side: str,
        trade_id: int
    ):
        """Open a new position"""
        position = Position(
            symbol=symbol,
            entry_price=entry_price,
            entry_time=time.time(),
            quantity=quantity,
            side=side,
            highest_price=entry_price,
            trade_id=trade_id
        )
        self.positions[symbol] = position
        logger.info(f"📍 Position opened: {symbol} {side} {quantity:.6f} @ {entry_price:.4f}")

    def close_position(self, symbol: str, exit_price: float, reason: str) -> Optional[Position]:
        """Close a position"""
        if symbol not in self.positions:
            return None

        position = self.positions.pop(symbol)
        pnl_bps = ((exit_price - position.entry_price) / position.entry_price) * 10000

        # Record loss time for cooldown
        if pnl_bps < 0:
            self.last_loss_time[symbol] = time.time()

        logger.info(f"🔴 Position closed: {symbol} @ {exit_price:.4f} | "
                   f"PnL: {pnl_bps:+.1f} bps | Reason: {reason}")
        return position

    def update_position(self, symbol: str, current_price: float):
        """Update position tracking (for trailing stop)"""
        if symbol not in self.positions:
            return

        position = self.positions[symbol]
        # Update highest price for trailing stop
        if current_price > position.highest_price:
            old_high = position.highest_price
            position.highest_price = current_price
            logger.debug(f"📈 {symbol} new high: {old_high:.4f} -> {current_price:.4f}")

    def check_exits(self, symbol: str, current_price: float) -> Optional[str]:
        """
        Check if position should be exited
        Returns exit reason if should exit, None otherwise
        """
        if symbol not in self.positions:
            return None

        position = self.positions[symbol]
        current_time = time.time()

        # Calculate current PnL in bps
        pnl_bps = ((current_price - position.entry_price) / position.entry_price) * 10000
        time_in_position = current_time - position.entry_time

        # Check time stop (exit if not profitable after 3 minutes)
        if time_in_position > self.config.time_stop_seconds:
            if pnl_bps < 10:  # Not profitable enough
                return f"Time stop ({time_in_position:.0f}s, PnL: {pnl_bps:+.1f}bps)"

        # Check trailing stop (only active when in profit)
        if pnl_bps >= self.config.trail_activation_bps:
            # Calculate drawdown from highest price
            drawdown_from_high = ((position.highest_price - current_price) / position.highest_price) * 10000

            if drawdown_from_high >= self.config.trail_stop_bps:
                return f"Trail stop (high: {position.highest_price:.4f}, draw: {drawdown_from_high:.1f}bps)"

        return None

    def is_in_cooldown(self, symbol: str) -> bool:
        """Check if symbol is in cooldown after loss"""
        if symbol not in self.last_loss_time:
            return False

        time_since_loss = time.time() - self.last_loss_time[symbol]
        in_cooldown = time_since_loss < self.config.cooldown_after_loss_seconds

        if in_cooldown:
            remaining = self.config.cooldown_after_loss_seconds - time_since_loss
            logger.info(f"❄️ {symbol} in cooldown: {remaining:.0f}s remaining")

        return in_cooldown

    def has_position(self, symbol: str) -> bool:
        """Check if we have an open position for symbol"""
        return symbol in self.positions

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for symbol"""
        return self.positions.get(symbol)

    def get_all_positions(self) -> Dict[str, Position]:
        """Get all open positions"""
        return self.positions.copy()

    def summary(self) -> str:
        """Get summary of open positions"""
        if not self.positions:
            return "📊 Positions: None"

        lines = ["📊 Open Positions:"]
        for symbol, pos in self.positions.items():
            pnl_bps = ((pos.highest_price - pos.entry_price) / pos.entry_price) * 10000
            time_held = time.time() - pos.entry_time
            lines.append(f"  {symbol}: {pos.quantity:.6f} @ {pos.entry_price:.4f} | "
                        f"High: {pos.highest_price:.4f} | PnL: {pnl_bps:+.1f}bps | "
                        f"Time: {time_held:.0f}s")
        return "\n".join(lines)
