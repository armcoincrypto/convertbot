# ScalperBot v2.0 - VPS Deployment Guide

**Status:** Ready for deployment
**Date:** 2025-11-20

---

## 🚀 Quick Start: Deploy v2.0 to VPS

### Option 1: Keep v1.0 Running, Test v2.0 Locally First (Recommended)

```bash
# On your Mac/local machine
cd /path/to/convertbot/scalperbot

# Test v2.0 locally in DRY_RUN mode
echo "STRATEGY_VERSION=2.0" >> .env
python main.py

# Watch logs for v2.0 indicators and signals
# Let it run for 30-60 minutes to verify everything works
```

### Option 2: Deploy v2.0 Directly to VPS

```bash
# SSH into VPS
ssh root@207.180.212.142

# Navigate to scalperbot
cd /root/scalperbot

# Stop the bot
sudo systemctl stop scalperbot

# Pull latest code from GitHub
git fetch origin claude/setup-scalperbot-01Jn5fG1jJc7RB7ft4E2gc8k
git merge origin/claude/setup-scalperbot-01Jn5fG1jJc7RB7ft4E2gc8k

# Update .env to use v2.0
nano .env
```

**In nano, add or update this line:**
```env
STRATEGY_VERSION=2.0
```

**Also add this new parameter:**
```env
TIME_STOP_MIN_PROFIT_BPS=10.0
```

Press `Ctrl+X`, then `Y`, then `Enter` to save.

**Restart the bot:**
```bash
sudo systemctl restart scalperbot

# Check status
sudo systemctl status scalperbot

# Watch logs
tail -f bot.log
```

---

## 📋 What to Expect with v2.0

### Startup Messages

You should see:
```
🚀 ScalperBot v2.0 Initializing...
📦 Loading ScalperBot v2.0 components...
✅ v2.0 components loaded: Professional 4-filter strategy
```

### Signal Generation

v2.0 runs 4 filters for each symbol:
```
📊 BTC/USDT Strategy v2.0 Check:
  Filter 1 (Trend): Multi-TF aligned ✅
  Filter 2 (Squeeze): Squeeze: True, Expanding: True ✅
  Filter 3 (Volume): z=2.1, sustained=True ✅
  Filter 4 (Breakout): price=87500.00, required=87450.00, threshold=8.0bps ✅
✅ BTC/USDT - ALL 4 FILTERS PASSED - ENTRY SIGNAL GENERATED
```

### Position Opening

v2.0 shows detailed sizing and exit plans:
```
💰 Position Sizing for BTC/USDT:
  Quantity: 0.0345
  Notional: $3000.00
  Risk: $24.00 (0.80%)
  Stop Loss: 18.5 bps
  Position %: 23.1% of equity
  Limiting Factor: max_notional

📊 Exit Plan for BTC/USDT:
  Entry: $87000.00
  Stop Loss: $86839.00 (-18.5 bps)
  Take Profit: $87483.00 (+55.5 bps)
  Risk:Reward = 1:3.00
  Trailing: Activates @ $87260.50 (+30.0 bps)
  Trail Distance: 15.0 bps from high
  Time Stop: 180s if PnL < 10 bps
```

### Position Tracking

v2.0 shows enhanced position summaries:
```
📊 Open Positions (v2.0):
  BTC/USDT: 0.034500 @ $87000.00 | High: $87200.00 | PnL: +23.0bps | Time: 45s | Trail: ⚪ Inactive
    SL: $86839.00 | TP: $87483.00 | Trail @: $87260.50
```

---

## 🔍 Verification Checklist

After deploying v2.0, verify these are working:

### ✅ Startup
- [ ] Bot starts without errors
- [ ] Shows "v2.0" in initialization
- [ ] Loads v2.0 components successfully
- [ ] Telegram startup notification received

### ✅ Strategy Execution
- [ ] All 4 filters are being checked
- [ ] Multi-timeframe data loading (1m, 5m, 30m)
- [ ] ATR calculations showing in logs
- [ ] Volume z-scores being calculated

### ✅ Position Management
- [ ] Dynamic SL/TP calculated based on ATR
- [ ] Trailing stop activation prices set
- [ ] Position summaries show v2.0 format
- [ ] Time stop checking active

### ✅ Telegram Notifications
- [ ] Startup message received
- [ ] Trade opened messages show ATR info
- [ ] Trade closed messages show dynamic levels

---

## 🎛️ Configuration Options

### Conservative Settings (Start Here)

```env
# Use v2.0 with cautious parameters
STRATEGY_VERSION=2.0
DRY_RUN=true
STRATEGY_INTERVAL=60
MAX_POSITIONS=2
```

### Aggressive Settings (After Testing)

```env
# More active trading
STRATEGY_VERSION=2.0
STRATEGY_INTERVAL=30
MAX_POSITIONS=3
```

### Production Settings

```env
# Full live trading (after 7+ days DRY_RUN)
STRATEGY_VERSION=2.0
DRY_RUN=false
STRATEGY_INTERVAL=30
MAX_POSITIONS=3
```

---

## 🔄 Switching Between v1.0 and v2.0

It's easy to switch between versions:

### Switch to v2.0
```bash
# Edit .env
nano /root/scalperbot/.env

# Change this line:
STRATEGY_VERSION=2.0

# Restart
sudo systemctl restart scalperbot
```

### Switch back to v1.0
```bash
# Edit .env
nano /root/scalperbot/.env

# Change this line:
STRATEGY_VERSION=1.0

# Restart
sudo systemctl restart scalperbot
```

---

## 📊 Expected Performance Comparison

| Metric | v1.0 | v2.0 |
|--------|------|------|
| Signals/day | 1-3 | 5-15 |
| Win rate target | 55-65% | 60-70% |
| Avg profit/trade | 15-25 bps | 15-45 bps |
| Hold time | 3-10 min | 30s-5 min |
| Strategy complexity | Simple 4-filter | Professional 4-filter + multi-TF |
| Risk management | Fixed | ATR-based dynamic |
| Pair optimization | Generic | Pair-specific thresholds |

---

## 🐛 Troubleshooting

### Issue: Bot won't start
```bash
# Check logs
tail -50 /root/scalperbot/bot.log

# Common fixes:
# 1. Missing TIME_STOP_MIN_PROFIT_BPS parameter
echo "TIME_STOP_MIN_PROFIT_BPS=10.0" >> .env

# 2. Strategy version typo
# Make sure it's exactly: STRATEGY_VERSION=2.0
```

### Issue: No signals generated
```
# v2.0 is stricter - all 4 filters must pass
# Check logs to see which filter is failing:
tail -100 bot.log | grep "Filter"

# Common reasons:
# - 30m trend not bullish (requires patience)
# - BB not in squeeze (normal, wait for volatility)
# - Volume not surging (wait for active market)
```

### Issue: Import errors
```bash
# Make sure all new files are present
cd /root/scalperbot
ls -la indicators/
ls -la strategies/scalper_v2*
ls -la risk/stops.py
ls -la position_manager_v2.py
ls -la exec/sizer_v2.py

# If missing, pull again
git fetch origin claude/setup-scalperbot-01Jn5fG1jJc7RB7ft4E2gc8k
git reset --hard origin/claude/setup-scalperbot-01Jn5fG1jJc7RB7ft4E2gc8k
```

---

## 📈 Monitoring v2.0 Performance

### Real-time Monitoring

```bash
# Watch all activity
tail -f bot.log

# Watch only signals
tail -f bot.log | grep "Strategy v2.0 Check"

# Watch only positions
tail -f bot.log | grep "Open Positions"

# Watch only trades
tail -f bot.log | grep "TRADE"
```

### Daily Performance Check

```bash
# Check trade database
sqlite3 /root/scalperbot/trades.db

# In sqlite:
SELECT COUNT(*) as total_trades,
       AVG(pnl_bps) as avg_pnl,
       SUM(CASE WHEN pnl_bps > 0 THEN 1 ELSE 0 END) as wins
FROM trades
WHERE DATE(timestamp) = DATE('now');
```

---

## ⚠️ Important Reminders

1. **Start with DRY_RUN=true** - Test for at least 7 days
2. **Monitor Telegram** - Watch all notifications
3. **Check logs daily** - Look for errors or unusual behavior
4. **Don't switch strategies mid-day** - Let it run a full session
5. **Keep backups** - The database contains valuable performance data

---

## 🎯 Success Criteria Before Going Live

Before setting `DRY_RUN=false`, verify:

- [ ] 7+ days of DRY_RUN performance data
- [ ] Win rate > 55%
- [ ] Average PnL per trade > 0.15%
- [ ] No unhandled errors in logs
- [ ] All exit mechanisms tested (SL, TP, Trail, Time)
- [ ] Telegram notifications working reliably
- [ ] Position sizing calculations correct

---

## 📞 Support

If you encounter issues:
1. Check logs: `tail -100 /root/scalperbot/bot.log`
2. Verify .env settings
3. Confirm all files present with `ls -laR /root/scalperbot`
4. Check GitHub for latest commits

---

**Good luck with v2.0! Remember: Patience is key. Let the strategy work across multiple market conditions before judging performance.** 🚀
