"""
Position Manager v2.0 - Enhanced with dynamic ATR-based exits
Tracks open positions and manages exits with professional risk management
"""
import time
from typing import Dict, Optional
from dataclasses import dataclass, field
import logging

from risk.stops import DynamicStops, ExitChecker

logger = logging.getLogger(__name__)


@dataclass
class PositionV2:
    """Represents an open position with dynamic exit levels"""
    symbol: str
    entry_price: float
    entry_time: float
    quantity: float
    side: str  # 'buy' or 'sell'
    trade_id: int

    # Dynamic exit levels
    sl_price: float
    tp_price: float
    trail_activation_price: float
    trail_bps: float

    # ATR info
    atr_bps: float

    # Tracking
    highest_price: float = field(default=None)

    def __post_init__(self):
        if self.highest_price is None:
            self.highest_price = self.entry_price


class PositionManagerV2:
    """
    Enhanced position manager with dynamic ATR-based exits
    """

    def __init__(self, config):
        self.config = config
        self.positions: Dict[str, PositionV2] = {}
        self.last_loss_time: Dict[str, float] = {}
        self.dynamic_stops = DynamicStops()

    def open_position(
        self,
        symbol: str,
        entry_price: float,
        quantity: float,
        side: str,
        trade_id: int,
        atr_bps: float
    ) -> PositionV2:
        """
        Open a new position with dynamic exit levels

        Args:
            symbol: Trading pair
            entry_price: Entry price
            quantity: Position size
            side: 'buy' or 'sell'
            trade_id: Database trade ID
            atr_bps: Current ATR in basis points

        Returns:
            PositionV2 object
        """
        # Calculate dynamic exit levels
        exits = self.dynamic_stops.calculate_all_exits(symbol, entry_price, atr_bps)

        # Create position
        position = PositionV2(
            symbol=symbol,
            entry_price=entry_price,
            entry_time=time.time(),
            quantity=quantity,
            side=side,
            trade_id=trade_id,
            sl_price=exits['stop_loss']['sl_price'],
            tp_price=exits['take_profit']['tp_price'],
            trail_activation_price=exits['trailing_stop']['activation_price'],
            trail_bps=exits['trailing_stop']['trail_bps'],
            atr_bps=atr_bps,
            highest_price=entry_price
        )

        self.positions[symbol] = position

        # Log position and exit plan
        logger.info(f"📍 Position opened: {symbol} {side.upper()} {quantity:.6f} @ {entry_price:.4f}")
        self.dynamic_stops.log_exit_plan(exits)

        return position

    def close_position(
        self,
        symbol: str,
        exit_price: float,
        reason: str
    ) -> Optional[PositionV2]:
        """
        Close a position

        Args:
            symbol: Trading pair
            exit_price: Exit price
            reason: Exit reason

        Returns:
            Closed PositionV2 object
        """
        if symbol not in self.positions:
            return None

        position = self.positions.pop(symbol)

        # Calculate PnL
        pnl_bps = ((exit_price - position.entry_price) / position.entry_price) * 10000
        pnl_usd = (pnl_bps / 10000) * (position.entry_price * position.quantity)

        # Record loss time for cooldown
        if pnl_bps < 0:
            self.last_loss_time[symbol] = time.time()
            logger.info(f"❄️ {symbol} cooldown started (loss: {pnl_bps:.1f}bps)")

        # Log closure
        emoji = "🟢" if pnl_bps >= 0 else "🔴"
        logger.info(f"{emoji} Position closed: {symbol} @ {exit_price:.4f} | "
                   f"PnL: {pnl_bps:+.1f} bps (${pnl_usd:+.2f}) | Reason: {reason}")

        return position

    def update_position(self, symbol: str, current_price: float):
        """
        Update position tracking (highest price for trailing)

        Args:
            symbol: Trading pair
            current_price: Current market price
        """
        if symbol not in self.positions:
            return

        position = self.positions[symbol]

        # Update highest price for trailing stop
        if current_price > position.highest_price:
            old_high = position.highest_price
            position.highest_price = current_price

            # Check if trail just activated
            if old_high < position.trail_activation_price <= current_price:
                logger.info(f"🔔 {symbol} trailing stop ACTIVATED @ ${current_price:.4f} "
                           f"(+{position.trail_bps:.1f}bps from high)")
            else:
                logger.debug(f"📈 {symbol} new high: {old_high:.4f} -> {current_price:.4f}")

    def check_exits(self, symbol: str, current_price: float) -> Optional[str]:
        """
        Check all exit conditions for a position

        Args:
            symbol: Trading pair
            current_price: Current market price

        Returns:
            Exit reason if should exit, None otherwise
        """
        if symbol not in self.positions:
            return None

        position = self.positions[symbol]
        current_time = time.time()

        # Use ExitChecker to check all exits in priority order
        exit_reason = ExitChecker.check_all_exits(
            current_price=current_price,
            entry_price=position.entry_price,
            sl_price=position.sl_price,
            tp_price=position.tp_price,
            highest_price=position.highest_price,
            trail_activation_price=position.trail_activation_price,
            trail_bps=position.trail_bps,
            entry_time=position.entry_time,
            current_time=current_time,
            time_stop_seconds=self.config.time_stop_seconds,
            min_profit_bps=self.config.time_stop_min_profit_bps if hasattr(self.config, 'time_stop_min_profit_bps') else 10
        )

        return exit_reason

    def is_in_cooldown(self, symbol: str) -> bool:
        """
        Check if symbol is in cooldown after loss

        Args:
            symbol: Trading pair

        Returns:
            True if in cooldown
        """
        if symbol not in self.last_loss_time:
            return False

        time_since_loss = time.time() - self.last_loss_time[symbol]
        cooldown_seconds = self.config.cooldown_after_loss_seconds if hasattr(self.config, 'cooldown_after_loss_seconds') else 300

        in_cooldown = time_since_loss < cooldown_seconds

        if in_cooldown:
            remaining = cooldown_seconds - time_since_loss
            logger.debug(f"❄️ {symbol} in cooldown: {remaining:.0f}s remaining")

        return in_cooldown

    def has_position(self, symbol: str) -> bool:
        """Check if we have an open position for symbol"""
        return symbol in self.positions

    def get_position(self, symbol: str) -> Optional[PositionV2]:
        """Get position for symbol"""
        return self.positions.get(symbol)

    def get_all_positions(self) -> Dict[str, PositionV2]:
        """Get all open positions"""
        return self.positions.copy()

    def get_position_count(self) -> int:
        """Get number of open positions"""
        return len(self.positions)

    def summary(self) -> str:
        """Get summary of open positions"""
        if not self.positions:
            return "📊 Positions: None"

        lines = ["📊 Open Positions (v2.0):"]
        for symbol, pos in self.positions.items():
            current_pnl_bps = ((pos.highest_price - pos.entry_price) / pos.entry_price) * 10000
            time_held = time.time() - pos.entry_time

            # Check if trail is active
            trail_status = "🟢 ACTIVE" if pos.highest_price >= pos.trail_activation_price else "⚪ Inactive"

            lines.append(
                f"  {symbol}: {pos.quantity:.6f} @ ${pos.entry_price:.4f} | "
                f"High: ${pos.highest_price:.4f} | PnL: {current_pnl_bps:+.1f}bps | "
                f"Time: {time_held:.0f}s | Trail: {trail_status}"
            )
            lines.append(
                f"    SL: ${pos.sl_price:.4f} | TP: ${pos.tp_price:.4f} | "
                f"Trail @: ${pos.trail_activation_price:.4f}"
            )

        return "\n".join(lines)
