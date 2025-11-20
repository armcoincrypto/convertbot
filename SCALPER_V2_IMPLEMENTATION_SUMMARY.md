# ScalperBot v2.0 - Implementation Summary

**Status:** Core system complete, ready for integration testing

---

## ✅ Completed Phases (1-4)

### Phase 1: Professional Indicators ✅
**Files Created:**
- `indicators/trend.py` - Multi-timeframe EMA analysis (30m, 5m)
- `indicators/volatility.py` - ATR & Bollinger Band calculations
- `indicators/volume.py` - Z-score & percentile analysis

**Features:**
- 30m trend filter: EMA50 vs EMA200
- 5m momentum filter: EMA9 vs EMA21
- BB squeeze detection (bottom 30% percentile)
- BB expansion detection (>20% in 4 candles)
- Volume z-score with configurable thresholds
- Volume percentile analysis (85th-95th)
- Sustained volume checking (1-2 candle confirmation)

---

### Phase 2: Strategy Logic ✅
**Files Created:**
- `strategies/scalper_v2_config.py` - Pair-specific configuration
- `strategies/scalper_v2.py` - 4-filter entry system

**4-Filter Entry System:**
1. **Multi-timeframe Trend** - Both 30m and 5m must be bullish
2. **BB Squeeze → Expansion** - Volatility compression then expansion
3. **Volume Surge** - Z-score + percentile + sustained confirmation
4. **Breakout Confirmation** - Pair-specific thresholds with volatility adjustment

**Pair-Specific Thresholds:**
| Pair | Breakout | Volume Z-Score | Spread Limit | Expected Signals/Day |
|------|----------|----------------|--------------|---------------------|
| BTC/USDT | 8 bps | 1.7σ | 6 bps | 2-4 |
| ETH/USDT | 10 bps | 2.0σ | 8 bps | 3-6 |
| SOL/USDT | 12 bps | 2.3σ | 12 bps | 5-10 |
| XRP/USDT | 6 bps | 1.5σ | 10 bps | 1-3 |

---

### Phase 3: Dynamic Exit System ✅
**Files Created:**
- `risk/stops.py` - Dynamic SL/TP calculator
- `position_manager_v2.py` - Enhanced position tracking

**Exit System:**
- **Dynamic Stop Loss:** ATR × 1.5-2.2 (constrained 12-30 bps)
- **Dynamic Take Profit:** ATR × 3.0-4.0 (constrained 20-60 bps)
- **Trailing Stop:** ATR-based activation & trail distance
- **Time Stop:** Exit if not profitable after 2 minutes

**Exit Priority Order:**
1. Stop Loss (highest priority)
2. Take Profit
3. Trailing Stop (if activated)
4. Time Stop (if unprofitable)

---

### Phase 4: Execution & Sizing ✅
**Files Created:**
- `exec/sizer_v2.py` - ATR-based position sizing
- `exec/router.py` - Added depth checking method

**Position Sizing:**
- Risk: 0.8% of equity per trade
- ATR-adjusted for stop loss distance
- Multiple caps:
  - Max 25% of equity
  - Max $3,000 notional
  - Max $25,000 liquidity cap
  - Min $10 position size

**Depth Checking:**
- Requires 3x position size in liquidity
- Max 4 bps slippage tolerance
- Validates orderbook depth before execution

---

## 🔧 Integration Required (Phase 5)

### Option 1: Create Separate main_v2.py
- Keep v1.0 running
- Build new orchestrator for v2.0
- Test v2.0 independently
- **Time:** 1-2 hours

### Option 2: Add Strategy Switcher to main.py
- Add `STRATEGY_VERSION=2.0` to .env
- Conditional imports based on version
- Single codebase, switchable strategies
- **Time:** 1-2 hours

### Option 3: Gradual Integration
- Start with just v2.0 indicators in v1.0
- Add ATR-based exits to v1.0
- Gradually upgrade components
- **Time:** 2-3 hours, lower risk

---

## 📊 Expected Performance (v2.0)

Based on professional quant desk specifications:

| Metric | Target |
|--------|--------|
| Signals per day | 5-15 (across 4 pairs) |
| Win rate | 60-70% |
| Avg profit per trade | 0.15% - 0.45% |
| Hold time | 30s - 5 minutes |
| Max drawdown | < 5% |
| Sharpe ratio | > 1.5 |

---

## 🚀 Next Steps

### Testing Phase:
1. Create integration point (main_v2.py or switcher)
2. Run DRY_RUN with live data for 24-48 hours
3. Verify all 4 filters working correctly
4. Confirm exits triggering properly
5. Check position sizing calculations
6. Monitor Telegram notifications

### Deployment Phase:
1. Deploy to VPS
2. Run DRY_RUN for 7 days
3. Analyze performance metrics
4. Fine-tune pair-specific thresholds
5. Gradually enable live trading (start with BTC only)
6. Scale to all 4 pairs after 100+ trades

---

## 📦 File Structure

```
scalperbot/
├── indicators/               # NEW - Phase 1
│   ├── __init__.py
│   ├── trend.py             # Multi-timeframe EMA
│   ├── volatility.py        # ATR & BB
│   └── volume.py            # Z-score & percentiles
│
├── strategies/
│   ├── momentum_breakout.py # OLD - v1.0 strategy
│   ├── scalper_v2.py        # NEW - v2.0 strategy
│   └── scalper_v2_config.py # NEW - Pair configs
│
├── risk/
│   ├── breaker.py           # Daily loss circuit breaker
│   └── stops.py             # NEW - Dynamic SL/TP
│
├── exec/
│   ├── router.py            # ENHANCED - Added depth check
│   └── sizer_v2.py          # NEW - ATR-based sizing
│
├── position_manager.py      # OLD - v1.0
├── position_manager_v2.py   # NEW - v2.0 with dynamic exits
├── main.py                  # Current orchestrator
└── main_v2.py               # TO BE CREATED
```

---

## 🎯 Key Improvements Over v1.0

| Feature | v1.0 | v2.0 |
|---------|------|------|
| Strategy | Simple 4-filter breakout | Multi-timeframe + pair-specific |
| Exits | Fixed 15 bps trail | ATR-based dynamic (12-60 bps) |
| Volume | Basic surge or disabled | Z-score + percentile + sustained |
| Position Sizing | Fixed $100 | ATR-based with multiple caps |
| Signals/day | 1-3 | 5-15 |
| Execution | Basic market order | Depth + slippage + spread checks |
| Risk Management | Trail + time stop | SL + TP + Trail + Time (all ATR-based) |

---

## 💡 Recommendation

**Start with Option 2 (Strategy Switcher):**
- Cleanest implementation
- Easy to compare v1.0 vs v2.0 performance
- Single deployment process
- Lower maintenance overhead

**Implementation:**
```python
# .env
STRATEGY_VERSION=2.0  # or 1.0

# main.py
if settings.strategy_version == "2.0":
    from strategies.scalper_v2 import ScalperV2Strategy
    from position_manager_v2 import PositionManagerV2
    from exec.sizer_v2 import PositionSizerV2
    strategy = ScalperV2Strategy(candle_store)
    position_manager = PositionManagerV2(settings)
    sizer = PositionSizerV2()
else:
    # Use v1.0 components
    from strategies.momentum_breakout import MomentumBreakoutStrategy
    ...
```

---

**Status:** Ready for integration and testing!
**Total Build Time:** ~4 hours (Phases 1-4)
**Remaining Work:** 2-3 hours (integration + testing)
