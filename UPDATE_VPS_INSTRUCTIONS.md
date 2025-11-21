# 🔄 Update Your VPS with Latest Convertbot Fixes

## Current Status
✅ All fixes committed to GitHub on branch: `claude/continue-convert-bot-01NaRqFFu8ZgiFs2xV29rW6z`
✅ TRX withdrawal support added
✅ Monitoring script added
✅ All previous bugs fixed

## What's Fixed
1. **TRX Withdrawals** - DASH → TRON swaps now correctly withdraw TRX instead of USDT
2. **Clean Withdrawal IDs** - Messages show clean IDs instead of raw tuples
3. **Monitoring Script** - Easy way to check system status
4. **All Previous Bugs** - XMR detection, row.get() errors, Armenian notifications, etc.

## Update Your VPS Now

SSH into your VPS and run these commands:

```bash
# Stop services
sudo systemctl stop convertbot-worker
sudo systemctl stop convertbot-bot

# Navigate to Convertbot directory
cd /root/Convertbot

# Stash any local changes
git stash

# Switch to new branch with all fixes
git fetch origin
git checkout claude/continue-convert-bot-01NaRqFFu8ZgiFs2xV29rW6z
git pull origin claude/continue-convert-bot-01NaRqFFu8ZgiFs2xV29rW6z

# Clear Python cache (IMPORTANT!)
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete

# Restart services
sudo systemctl start convertbot-worker
sudo systemctl start convertbot-bot

# Verify services are running
sudo systemctl status convertbot-worker --no-pager | head -10
sudo systemctl status convertbot-bot --no-pager | head -10
```

## Monitor Your System

Use the new monitoring script to check status:

```bash
cd /root/Convertbot
bash monitor_convertbot.sh
```

This will show you:
- Service status (worker + bot)
- Database statistics
- Recent deposits
- Recent log activity
- Any errors

## Test TRX Withdrawal

To verify the TRX withdrawal fix works:

1. Open Telegram and go to @Conodbot
2. Send: `/start`
3. Choose: "💎 Dash → TRON"
4. Send a small test amount: 0.05 DASH (about $1.50)
5. Submit your TRX (TRC20) withdrawal address
6. Wait for 12 confirmations (~30 minutes)
7. Watch the logs: `tail -f /root/Convertbot/logs/worker.log`

You should see:
```
💱 Converting USDT → TRX on MEXC...
✅ Bought X TRX with Y USDT
✅ TRX Withdrawal successful: [withdrawal_id]
```

And receive TRX (not USDT) in your wallet!

## Quick Status Check

```bash
# View worker log
tail -f /root/Convertbot/logs/worker.log

# View bot log
tail -f /root/Convertbot/logs/bot.log

# Check database
sqlite3 /root/Convertbot/swapbot.db "SELECT txid, coin, output_coin, status FROM deposits ORDER BY inserted_at DESC LIMIT 5"
```

## Troubleshooting

If services fail to start:

```bash
# Check for errors
journalctl -u convertbot-worker -n 50 --no-pager
journalctl -u convertbot-bot -n 50 --no-pager

# Verify Python packages
source /root/Convertbot/venv/bin/activate
pip install -r requirements.txt

# Restart
sudo systemctl restart convertbot-worker
sudo systemctl restart convertbot-bot
```

## Support

If you encounter issues:
1. Run: `bash monitor_convertbot.sh` and share the output
2. Check logs: `tail -50 /root/Convertbot/logs/worker.log`
3. Verify database: `sqlite3 /root/Convertbot/swapbot.db ".schema deposits"`

---

**Next Steps After Update:**
1. ✅ Update VPS with new code
2. ✅ Verify both services are running
3. ✅ Test DASH → TRON swap with small amount
4. ✅ Monitor logs to confirm TRX withdrawal works
