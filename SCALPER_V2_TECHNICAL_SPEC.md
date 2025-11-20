# ScalperBot v2.0 - Professional Multi-Pair Scalping System
## Complete Technical Specification

**Version:** 2.0
**Date:** 2025-11-20
**Author:** Claude (Anthropic)
**Target Pairs:** BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT
**Exchange:** MEXC
**Timeframes:** 1m (primary), 5m, 30m

---

## 1. System Architecture

### 1.1 Overview
Professional cryptocurrency scalping bot using multi-timeframe analysis, dynamic volatility-based exits, and pair-specific thresholds optimized for each asset's unique characteristics.

### 1.2 Key Design Principles
- **Asset-Specific Logic:** Each pair has unique breakout, volume, and volatility thresholds
- **Multi-Timeframe Confirmation:** 30m trend + 5m momentum + 1m execution
- **Dynamic Risk:** ATR-based stops and targets (not fixed bps)
- **Quality over Quantity:** Strict filtering for high win-rate signals
- **Execution Safety:** Depth checking, slippage guards, spread limits

### 1.3 Expected Performance
- **Signals per day:** 5-15 total across 4 pairs
- **Expectancy per trade:** 0.15% - 0.45%
- **Win rate target:** 60-70%
- **Max positions:** 3 concurrent
- **Holding time:** 30 seconds - 5 minutes

---

## 2. Data Requirements

### 2.1 Candlestick Data (OHLCV)
```python
{
    '1m':  500 candles per pair  # Primary execution timeframe
    '5m':  200 candles per pair  # Momentum confirmation
    '30m': 100 candles per pair  # Trend filter
}
```

### 2.2 Orderbook Data (Real-time)
```python
{
    'bids': List[Tuple[price, size]],  # Top 20 levels
    'asks': List[Tuple[price, size]],  # Top 20 levels
    'timestamp': int
}
```

### 2.3 Calculated Indicators (Per Pair)
```python
# Trend indicators (30m)
ema_50_30m: float
ema_200_30m: float

# Momentum indicators (5m)
ema_9_5m: float
ema_21_5m: float

# Volatility indicators (1m)
atr_14_1m: float        # 14-period ATR in bps
bb_upper_1m: float      # Bollinger Band upper (20, 2.0)
bb_lower_1m: float      # Bollinger Band lower
bb_width_1m: float      # Distance between bands
bb_width_pct: float     # Percentile of BB width (last 48h)

# Volume indicators (1m)
volume_zscore: float    # Z-score of current volume
volume_p90: float       # 90th percentile last 24h
volume_p95: float       # 95th percentile last 24h

# Price action
high_10m: float         # Highest high last 10 candles (1m)
```

---

## 3. Entry Logic

### 3.1 Multi-Timeframe Trend Filter (Required for ALL pairs)

```python
def check_trend_filter(pair: str) -> bool:
    """
    30m: Long-term trend must be bullish
    5m: Short-term momentum must be bullish
    """
    # 30m trend check
    if ema_50_30m <= ema_200_30m:
        return False  # Trend not bullish

    # 5m momentum check
    if ema_9_5m <= ema_21_5m:
        return False  # Momentum not bullish

    return True
```

### 3.2 Bollinger Band Squeeze Detection

```python
def check_bb_squeeze(pair: str) -> bool:
    """
    BB width must be in bottom 30% of last 48 hours
    AND expanding by > 20% in last 3-4 candles
    """
    # Get BB width percentile rank over last 48h (2880 1m candles)
    bb_percentile = get_percentile_rank(bb_width_1m, lookback=2880)

    if bb_percentile > 0.30:
        return False  # Not squeezed enough

    # Check expansion
    bb_width_4_candles_ago = get_bb_width(offset=4)
    expansion_pct = (bb_width_1m - bb_width_4_candles_ago) / bb_width_4_candles_ago

    if expansion_pct < 0.20:
        return False  # Not expanding enough

    return True
```

### 3.3 Volume Surge Detection (Pair-Specific)

```python
VOLUME_THRESHOLDS = {
    'BTC/USDT': {'zscore': 1.7, 'percentile': 0.95, 'sustained_candles': 1},
    'ETH/USDT': {'zscore': 2.0, 'percentile': 0.90, 'sustained_candles': 1},
    'SOL/USDT': {'zscore': 2.3, 'percentile': 0.90, 'sustained_candles': 1},
    'XRP/USDT': {'zscore': 1.5, 'percentile': 0.85, 'sustained_candles': 2},
}

def check_volume_surge(pair: str) -> bool:
    """
    Volume must exceed z-score threshold
    AND be above percentile threshold
    AND be sustained for N candles (pair-specific)
    """
    config = VOLUME_THRESHOLDS[pair]

    # Z-score check
    if volume_zscore < config['zscore']:
        return False

    # Percentile check
    volume_threshold = get_percentile(volumes_24h, config['percentile'])
    if current_volume < volume_threshold:
        return False

    # Sustained volume check (for XRP mainly)
    if config['sustained_candles'] > 1:
        for i in range(1, config['sustained_candles']):
            if get_volume(offset=i) < volume_threshold * 0.8:
                return False  # Volume dropped too much

    return True
```

### 3.4 Breakout Confirmation (Pair-Specific)

```python
BREAKOUT_THRESHOLDS = {
    'BTC/USDT': {'bps': 8,  'volatility_adjusted': True},
    'ETH/USDT': {'bps': 10, 'volatility_adjusted': True},
    'SOL/USDT': {'bps': 12, 'volatility_adjusted': True},
    'XRP/USDT': {'bps': 6,  'volatility_adjusted': False},
}

ATR_VOLATILITY_LIMITS = {
    'BTC/USDT': {'normal': (7, 18),   'high': 20, 'high_adjustment': +4},
    'ETH/USDT': {'normal': (10, 25),  'high': 30, 'high_adjustment': +5},
    'SOL/USDT': {'normal': (20, 50),  'high': 60, 'high_adjustment': +8},
    'XRP/USDT': {'normal': (5, 12),   'high': 15, 'high_adjustment': +3},
}

def check_breakout(pair: str, current_price: float) -> bool:
    """
    Price must close above 10m high by threshold bps
    Threshold increases in high volatility environments
    """
    config = BREAKOUT_THRESHOLDS[pair]
    vol_config = ATR_VOLATILITY_LIMITS[pair]

    # Get 10-minute high (last 10 1m candles)
    high_10m = get_high(lookback=10)

    # Base threshold
    threshold_bps = config['bps']

    # Adjust for high volatility
    if config['volatility_adjusted']:
        if atr_14_1m > vol_config['high']:
            threshold_bps += vol_config['high_adjustment']

    # Calculate required breakout price
    required_price = high_10m * (1 + threshold_bps / 10000)

    if current_price < required_price:
        return False

    return True
```

### 3.5 Final Entry Signal

```python
def generate_entry_signal(pair: str) -> Optional[dict]:
    """
    All filters must pass for entry
    """
    # Filter 1: Trend
    if not check_trend_filter(pair):
        log(f"❌ {pair} - Trend filter failed")
        return None

    # Filter 2: BB Squeeze → Expansion
    if not check_bb_squeeze(pair):
        log(f"❌ {pair} - BB squeeze filter failed")
        return None

    # Filter 3: Volume Surge
    if not check_volume_surge(pair):
        log(f"❌ {pair} - Volume surge filter failed")
        return None

    # Filter 4: Breakout
    current_price = get_current_price(pair)
    if not check_breakout(pair, current_price):
        log(f"❌ {pair} - Breakout filter failed")
        return None

    # All filters passed
    log(f"✅ {pair} - ALL FILTERS PASSED - ENTRY SIGNAL")

    return {
        'symbol': pair,
        'action': 'BUY',
        'price': current_price,
        'timestamp': time.time(),
        'filters_passed': ['trend', 'squeeze', 'volume', 'breakout'],
        'atr': atr_14_1m,
        'volume_zscore': volume_zscore
    }
```

---

## 4. Pre-Execution Checks

### 4.1 Spread Check (Pair-Specific)

```python
SPREAD_LIMITS = {
    'BTC/USDT': 6,   # bps
    'ETH/USDT': 8,   # bps
    'SOL/USDT': 12,  # bps
    'XRP/USDT': 10,  # bps
}

def check_spread(pair: str) -> bool:
    """
    Spread must be within acceptable limits
    """
    spread_bps = get_spread_bps(pair)
    limit = SPREAD_LIMITS[pair]

    if spread_bps > limit:
        log(f"⚠️ {pair} - Spread too wide: {spread_bps:.1f} > {limit} bps")
        return False

    return True
```

### 4.2 Depth Check

```python
def check_depth(pair: str, notional_usd: float) -> bool:
    """
    Order book depth must be at least 3x position size
    """
    orderbook = get_orderbook(pair)

    # Calculate available liquidity at best ask
    best_ask = orderbook['asks'][0][0]

    # Sum liquidity within 4 bps of best ask
    liquidity_usd = 0
    for price, size in orderbook['asks']:
        if price <= best_ask * 1.0004:  # Within 4 bps
            liquidity_usd += price * size
        else:
            break

    required_liquidity = notional_usd * 3

    if liquidity_usd < required_liquidity:
        log(f"⚠️ {pair} - Insufficient depth: ${liquidity_usd:.0f} < ${required_liquidity:.0f}")
        return False

    return True
```

### 4.3 Cooldown Check

```python
def check_cooldown(pair: str) -> bool:
    """
    No trading if recently stopped out (5 min cooldown)
    """
    if is_in_cooldown(pair):
        remaining = get_cooldown_remaining(pair)
        log(f"❄️ {pair} - In cooldown: {remaining}s remaining")
        return False

    return True
```

### 4.4 Position Check

```python
def check_max_positions() -> bool:
    """
    Max 3 concurrent positions
    """
    open_positions = get_open_position_count()

    if open_positions >= 3:
        log(f"⚠️ Max positions reached: {open_positions}/3")
        return False

    return True
```

---

## 5. Position Sizing

### 5.1 Smart Position Sizing Logic

```python
def calculate_position_size(
    pair: str,
    entry_price: float,
    atr_bps: float,
    equity_usd: float
) -> dict:
    """
    Dynamic position sizing based on:
    - Risk percentage (0.8% of equity)
    - ATR-based stop loss
    - Notional cap (3,000 USDT max)
    - Liquidity cap (25,000 USDT max)
    """
    # Risk parameters
    RISK_PCT = 0.008  # 0.8% of equity per trade
    MAX_POSITION_PCT = 0.25  # Max 25% of equity in one position
    MAX_NOTIONAL = 3000  # USDT
    MAX_LIQUIDITY_CAP = 25000  # USDT

    # Calculate stop loss distance (based on ATR)
    sl_bps = calculate_stop_loss_bps(pair, atr_bps)

    # Risk amount in USD
    risk_usd = equity_usd * RISK_PCT

    # Position size based on risk
    position_usd = risk_usd / (sl_bps / 10000)

    # Apply caps
    max_position_usd = equity_usd * MAX_POSITION_PCT
    position_usd = min(position_usd, max_position_usd, MAX_NOTIONAL, MAX_LIQUIDITY_CAP)

    # Convert to quantity
    quantity = position_usd / entry_price

    return {
        'quantity': quantity,
        'notional_usd': position_usd,
        'risk_usd': risk_usd,
        'sl_bps': sl_bps,
        'can_trade': position_usd >= 10  # Min $10 position
    }
```

---

## 6. Exit Logic

### 6.1 Stop Loss (ATR-Based, Pair-Specific)

```python
def calculate_stop_loss_bps(pair: str, atr_bps: float) -> float:
    """
    Stop loss based on ATR multiplier
    Different multipliers for each pair
    """
    ATR_MULTIPLIERS = {
        'BTC/USDT': 1.5,
        'ETH/USDT': 1.8,
        'SOL/USDT': 2.0,
        'XRP/USDT': 2.2,
    }

    multiplier = ATR_MULTIPLIERS[pair]
    sl_bps = atr_bps * multiplier

    # Floor and ceiling
    sl_bps = max(12, min(sl_bps, 30))  # Between 12-30 bps

    return sl_bps
```

### 6.2 Take Profit (ATR-Based)

```python
def calculate_take_profit_bps(pair: str, atr_bps: float) -> float:
    """
    Take profit based on ATR
    Target 2-3x stop loss distance
    """
    ATR_TP_MULTIPLIERS = {
        'BTC/USDT': 3.0,
        'ETH/USDT': 3.5,
        'SOL/USDT': 4.0,
        'XRP/USDT': 3.2,
    }

    multiplier = ATR_TP_MULTIPLIERS[pair]
    tp_bps = atr_bps * multiplier

    # Floor and ceiling
    tp_bps = max(20, min(tp_bps, 60))  # Between 20-60 bps

    return tp_bps
```

### 6.3 Trailing Stop

```python
def calculate_trailing_stop(pair: str, atr_bps: float) -> dict:
    """
    Trailing stop activates after minimum profit
    Trail distance based on ATR
    """
    # Activation threshold
    activation_bps = atr_bps * 1.5
    activation_bps = max(15, min(activation_bps, 25))

    # Trail distance (tighter than initial SL)
    trail_bps = atr_bps * 1.2
    trail_bps = max(10, min(trail_bps, 20))

    return {
        'activation_bps': activation_bps,
        'trail_bps': trail_bps
    }
```

### 6.4 Time Stop

```python
TIME_STOP_SECONDS = 120  # 2 minutes

def check_time_stop(position: Position) -> Optional[str]:
    """
    Exit if position not profitable after 2 minutes
    """
    time_in_position = time.time() - position.entry_time

    if time_in_position > TIME_STOP_SECONDS:
        current_pnl_bps = calculate_pnl_bps(position)

        if current_pnl_bps < 10:  # Less than 10 bps profit
            return f"Time stop ({time_in_position:.0f}s, PnL: {current_pnl_bps:+.1f}bps)"

    return None
```

### 6.5 Exit Priority Order

```python
def check_exits(position: Position, current_price: float) -> Optional[str]:
    """
    Check all exit conditions in priority order
    """
    # 1. Stop Loss (highest priority)
    if current_price <= position.stop_loss_price:
        return "Stop Loss"

    # 2. Take Profit
    if current_price >= position.take_profit_price:
        return "Take Profit"

    # 3. Trailing Stop (if activated)
    if position.highest_price >= position.trail_activation_price:
        drawdown_from_high = (position.highest_price - current_price) / position.highest_price * 10000
        if drawdown_from_high >= position.trail_stop_bps:
            return f"Trailing Stop (high: {position.highest_price:.4f})"

    # 4. Time Stop
    time_stop_reason = check_time_stop(position)
    if time_stop_reason:
        return time_stop_reason

    return None
```

---

## 7. Order Execution

### 7.1 Market Order with Slippage Guard

```python
MAX_SLIPPAGE_BPS = 4  # Maximum 4 bps slippage

def execute_market_order(
    pair: str,
    side: str,
    quantity: float,
    expected_price: float
) -> Optional[dict]:
    """
    Execute market order with slippage protection
    """
    # Place order
    order = exchange.create_market_order(pair, side, quantity)

    if not order:
        log(f"❌ {pair} - Order failed to execute")
        return None

    # Check slippage
    filled_price = order['price']
    slippage_bps = abs(filled_price - expected_price) / expected_price * 10000

    if slippage_bps > MAX_SLIPPAGE_BPS:
        log(f"⚠️ {pair} - High slippage: {slippage_bps:.1f} bps")
        # Log but don't cancel (order already filled)

    log(f"✅ {pair} - Order filled @ {filled_price:.4f} (slippage: {slippage_bps:.1f}bps)")

    return order
```

---

## 8. Configuration Structure

### 8.1 Environment Variables (.env)

```bash
# Exchange
MEXC_API_KEY=your_key
MEXC_API_SECRET=your_secret

# Mode
DRY_RUN=true

# Trading Pairs
TRADING_PAIRS=BTC/USDT,ETH/USDT,SOL/USDT,XRP/USDT

# Intervals
STRATEGY_INTERVAL=30  # Run strategy every 30 seconds
DATA_POLL_INTERVAL=5  # Poll data every 5 seconds

# Position Sizing
RISK_PCT=0.008  # 0.8% risk per trade
MAX_POSITION_PCT=0.25  # Max 25% equity per position
MAX_NOTIONAL=3000  # Max $3000 per position
MAX_POSITIONS=3  # Max 3 concurrent positions

# Risk Management
DAILY_LOSS_LIMIT_PCT=3.0
COOLDOWN_AFTER_LOSS_SECONDS=300

# Telegram
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# Logging
LOG_LEVEL=INFO
LOG_FILE=bot.log
```

### 8.2 Pair-Specific Config (Python)

```python
# strategies/scalper_v2_config.py

PAIR_CONFIG = {
    'BTC/USDT': {
        'breakout_bps': 8,
        'volume_zscore': 1.7,
        'volume_percentile': 0.95,
        'sustained_candles': 1,
        'spread_limit_bps': 6,
        'atr_normal_range': (7, 18),
        'atr_high_threshold': 20,
        'atr_sl_multiplier': 1.5,
        'atr_tp_multiplier': 3.0,
    },
    'ETH/USDT': {
        'breakout_bps': 10,
        'volume_zscore': 2.0,
        'volume_percentile': 0.90,
        'sustained_candles': 1,
        'spread_limit_bps': 8,
        'atr_normal_range': (10, 25),
        'atr_high_threshold': 30,
        'atr_sl_multiplier': 1.8,
        'atr_tp_multiplier': 3.5,
    },
    'SOL/USDT': {
        'breakout_bps': 12,
        'volume_zscore': 2.3,
        'volume_percentile': 0.90,
        'sustained_candles': 1,
        'spread_limit_bps': 12,
        'atr_normal_range': (20, 50),
        'atr_high_threshold': 60,
        'atr_sl_multiplier': 2.0,
        'atr_tp_multiplier': 4.0,
    },
    'XRP/USDT': {
        'breakout_bps': 6,
        'volume_zscore': 1.5,
        'volume_percentile': 0.85,
        'sustained_candles': 2,
        'spread_limit_bps': 10,
        'atr_normal_range': (5, 12),
        'atr_high_threshold': 15,
        'atr_sl_multiplier': 2.2,
        'atr_tp_multiplier': 3.2,
    },
}
```

---

## 9. Logging & Monitoring

### 9.1 Required Log Messages

```python
# Entry signals
"📊 {pair} Strategy Check: Trend={trend}, Squeeze={squeeze}, Volume={vol}, Breakout={bo}"
"✅ {pair} - ALL FILTERS PASSED - ENTRY SIGNAL"

# Pre-execution checks
"✅ {pair} - Pre-execution checks: Spread={spread_bps}bps, Depth=${depth_usd}, Positions={n}/3"

# Execution
"🟢 TRADE OPENED: {pair} BUY @ {price} | Size: {qty} (${notional}) | SL: {sl_price} | TP: {tp_price}"

# Exits
"🔴 TRADE CLOSED: {pair} @ {exit_price} | PnL: {pnl_bps:+.1f}bps (${pnl_usd:+.2f}) | Reason: {reason}"

# Position updates
"📈 {pair} new high: {old_high} -> {new_high} | Trail activated @ {trail_activation_price}"

# Errors
"❌ {pair} - {error_type}: {error_details}"
```

### 9.2 Performance Metrics (Logged every hour)

```python
{
    'timestamp': '2025-11-20 23:00:00',
    'total_trades': 12,
    'wins': 8,
    'losses': 4,
    'win_rate': 0.667,
    'total_pnl_bps': 142.5,
    'total_pnl_usd': 28.50,
    'avg_win_bps': 25.3,
    'avg_loss_bps': -14.2,
    'sharpe_ratio': 1.85,
    'by_pair': {
        'BTC/USDT': {'trades': 3, 'pnl_bps': 45.2},
        'ETH/USDT': {'trades': 4, 'pnl_bps': 52.8},
        'SOL/USDT': {'trades': 4, 'pnl_bps': 38.1},
        'XRP/USDT': {'trades': 1, 'pnl_bps': 6.4},
    }
}
```

---

## 10. Telegram Notifications

### 10.1 Enhanced Notifications

```python
# Entry notification
"""
🟢 TRADE OPENED

BTC/USDT BUY
Entry: $87,234.50
Size: 0.0345 BTC ($3,000)

Risk Management:
SL: $87,104 (-15 bps)
TP: $87,496 (+30 bps)
Trail: Activates @ +20 bps

Signal Quality:
Volume: 2.1σ (95th percentile)
ATR: 12.5 bps
BB Squeeze: 18th percentile

Time: 2025-11-20 23:15:30
"""

# Exit notification
"""
🟢 TRADE CLOSED - PROFIT

BTC/USDT
Entry: $87,234.50
Exit: $87,458.20
PnL: +25.6 bps ($8.88)

Reason: Trailing Stop
High: $87,496.30 (+30 bps)
Drawdown: 15.2 bps from high

Hold time: 3m 42s

Time: 2025-11-20 23:19:12
"""
```

---

## 11. DRY_RUN Implementation

### 11.1 Simulated Execution

```python
class DryRunExecution:
    """
    Realistic order simulation with slippage
    """

    def simulate_market_order(self, pair, side, quantity, current_price):
        # Simulate realistic slippage (1-3 bps)
        slippage_bps = random.uniform(1, 3)

        if side == 'buy':
            filled_price = current_price * (1 + slippage_bps / 10000)
        else:
            filled_price = current_price * (1 - slippage_bps / 10000)

        # Simulate order object
        return {
            'id': f'DRY_RUN_{int(time.time())}',
            'symbol': pair,
            'side': side,
            'price': filled_price,
            'amount': quantity,
            'cost': filled_price * quantity,
            'status': 'closed',
            'timestamp': int(time.time() * 1000)
        }

    def simulate_balance_update(self, pnl_usd):
        self.simulated_balance += pnl_usd
```

---

## 12. File Structure

```
scalperbot/
├── config.py                          # Settings (Pydantic)
├── main.py                            # Main orchestrator
├── db.py                              # Trade logging
├── telegram_notifier.py               # Telegram alerts
├── position_manager.py                # Position tracking
│
├── exchanges/
│   └── adapter.py                     # MEXC adapter
│
├── datafeed/
│   ├── candle_store.py                # Multi-timeframe candle storage
│   ├── orderbook.py                   # Orderbook management
│   └── rest_poller.py                 # Data polling
│
├── strategies/
│   ├── scalper_v2.py                  # NEW: Professional scalper strategy
│   ├── scalper_v2_config.py           # NEW: Pair-specific config
│   └── momentum_breakout.py           # OLD: Simple strategy (backup)
│
├── indicators/
│   ├── trend.py                       # NEW: EMA calculations (30m, 5m)
│   ├── volatility.py                  # NEW: ATR, BB calculations
│   └── volume.py                      # NEW: Z-score, percentile
│
├── exec/
│   ├── router.py                      # Order execution
│   └── sizer.py                       # NEW: Advanced position sizing
│
└── risk/
    ├── breaker.py                     # Daily loss circuit breaker
    └── stops.py                       # NEW: Dynamic SL/TP logic
```

---

## 13. Implementation Phases

### Phase 1: Core Indicators (2-3 hours)
- Multi-timeframe EMA calculations
- ATR calculation (1m, 5m)
- BB calculations with percentile tracking
- Volume z-score and percentile calculations

### Phase 2: Strategy Logic (2-3 hours)
- Implement 4-filter entry system
- Pair-specific threshold configuration
- Signal generation with all checks

### Phase 3: Exit System (1-2 hours)
- ATR-based dynamic SL/TP
- Trailing stop logic
- Time stop
- Exit priority manager

### Phase 4: Execution & Risk (1-2 hours)
- Advanced position sizer
- Depth checking
- Slippage guards
- Pre-execution filter pipeline

### Phase 5: Testing & Deployment (2-3 hours)
- Unit tests for each component
- DRY_RUN testing with live data
- Performance monitoring
- VPS deployment

**Total estimated time: 8-13 hours**

---

## 14. Success Criteria

### 14.1 Before Going Live
- [ ] DRY_RUN for minimum 7 days
- [ ] Win rate > 55%
- [ ] Average PnL per trade > 0.15%
- [ ] Max drawdown < 5%
- [ ] All exit mechanisms tested
- [ ] Telegram alerts working
- [ ] No execution errors for 24h

### 14.2 Live Trading Checklist
- [ ] Start with 1 pair only (BTC/USDT)
- [ ] Max $100 position size initially
- [ ] Monitor first 20 trades manually
- [ ] Gradually increase to all 4 pairs
- [ ] Scale position sizes after 100+ trades

---

## 15. Key Differences from v1.0

| Feature | v1.0 (Current) | v2.0 (Professional) |
|---------|----------------|---------------------|
| Strategy | Simple 4-filter breakout | Multi-timeframe with pair-specific logic |
| Exits | Fixed bps (15 bps trail) | ATR-based dynamic (12-60 bps) |
| Volume | Basic surge or disabled | Z-score + percentile + sustained |
| Position Sizing | Fixed $100 | Dynamic ATR-based with caps |
| Signals/day | 1-3 | 5-15 |
| Execution | Basic market order | Depth + slippage + spread checks |
| Risk | Trailing + time stop | SL + TP + Trail + Time + ATR-based |

---

**END OF SPECIFICATION**

This document provides the complete technical blueprint for implementing ScalperBot v2.0.

Next steps:
1. Review this specification
2. Approve implementation approach
3. Begin Phase 1 development

