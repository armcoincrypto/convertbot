# Convertbot - Operations Guide

VPS deployment, monitoring, and troubleshooting procedures.

## VPS Information

- **Path**: `/root/Convertbot`
- **Database**: `/root/Convertbot/swapbot.db`
- **Logs**: `/root/Convertbot/logs/`

## Service Management

### Start Services

```bash
systemctl start convertbot-bot.service
systemctl start convertbot-worker.service
```

Or both:
```bash
systemctl restart convertbot-worker.service convertbot-bot.service
```

### Stop Services

```bash
systemctl stop convertbot-bot.service
systemctl stop convertbot-worker.service
```

### Check Status

```bash
systemctl status convertbot-worker.service convertbot-bot.service
```

### View Service Logs

```bash
journalctl -u convertbot-worker.service -f
journalctl -u convertbot-bot.service -f
```

## Deploying Changes

### Standard Deployment

```bash
cd /root/Convertbot
git fetch origin <branch>
git reset --hard origin/<branch>
systemctl restart convertbot-worker.service convertbot-bot.service
```

### Quick Deploy Script

```bash
#!/bin/bash
BRANCH=${1:-main}
cd /root/Convertbot
git fetch origin $BRANCH
git reset --hard origin/$BRANCH
systemctl restart convertbot-worker.service convertbot-bot.service
echo "Deployed $BRANCH"
```

## Log Monitoring

### View Worker Logs

```bash
tail -f /root/Convertbot/logs/worker.log
```

### View Error Logs

```bash
tail -f /root/Convertbot/logs/worker-error.log
```

### View Recent Activity

```bash
tail -100 /root/Convertbot/logs/worker.log | grep -E "(PIPELINE|Withdrawal|Trade)"
```

### Search for Specific TXID

```bash
grep "abc123" /root/Convertbot/logs/worker.log
```

## Database Queries

### Check Deposit Status Distribution

```bash
sqlite3 swapbot.db "SELECT status, COUNT(*) FROM deposits GROUP BY status;"
```

### View Recent Deposits

```bash
sqlite3 swapbot.db "SELECT substr(txid,1,16), coin, status, confs FROM deposits ORDER BY inserted_at DESC LIMIT 10;"
```

### View Stuck Deposits

```bash
sqlite3 swapbot.db "SELECT txid, coin, status, confs, required_confs FROM deposits WHERE status IN ('CONFIRMING', 'CONFIRMED', 'SOLD');"
```

### View Failed Deposits

```bash
sqlite3 swapbot.db "SELECT txid, coin, status, user_id FROM deposits WHERE status LIKE '%FAILED%' OR status = 'PROCESSING_ERROR';"
```

### Get Deposit Details

```bash
sqlite3 swapbot.db "SELECT * FROM deposits WHERE txid LIKE 'abc123%';"
```

### Count Successful Withdrawals

```bash
sqlite3 swapbot.db "SELECT COUNT(*) FROM deposits WHERE status = 'WITHDRAWN';"
```

### View User's Deposits

```bash
sqlite3 swapbot.db "SELECT txid, coin, status, final_usdt FROM deposits WHERE user_id = 123456789;"
```

## Manual Interventions

### Reset TRADE_FAILED to Retry

```bash
sqlite3 swapbot.db "UPDATE deposits SET status = 'CONFIRMED' WHERE txid = 'YOUR_TXID';"
```

### Mark as Manually Processed

```bash
sqlite3 swapbot.db "UPDATE deposits SET status = 'WITHDRAWN' WHERE txid = 'YOUR_TXID';"
```

### Manual USDT Withdrawal

```python
python3 << 'EOF'
import asyncio
from libs.mexc_client import MEXCClient
from app.config import settings
from app import db

async def manual_withdraw():
    mexc = MEXCClient(settings.mexc_api_key, settings.mexc_api_secret)
    txid = "YOUR_TXID"
    address = "USER_TRC20_ADDRESS"
    amount = 100.00  # USDT amount

    success, result = mexc.withdraw_usdt_trc20(address, amount)
    if success:
        print(f"Sent! ID: {result.get('withdraw_id')}")
        await db.update_deposit_status(txid, 'WITHDRAWN')
    else:
        print(f"Failed: {result}")

asyncio.run(manual_withdraw())
EOF
```

### Check MEXC Balance

```python
python3 << 'EOF'
from libs.mexc_client import MEXCClient
from app.config import settings

mexc = MEXCClient(settings.mexc_api_key, settings.mexc_api_secret)
balances = mexc.get_account_balance()
for coin, amounts in balances.items():
    print(f"{coin}: {amounts['free']:.4f} (locked: {amounts['locked']:.4f})")
EOF
```

### Check MEXC Deposit History

```python
python3 << 'EOF'
from libs.mexc_client import MEXCClient
from app.config import settings

mexc = MEXCClient(settings.mexc_api_key, settings.mexc_api_secret)
deposits = mexc.get_deposit_history(limit=10)
for d in deposits:
    print(f"{d['coin']}: {d['amount']} - Status {d['status']} - {d.get('txId', 'N/A')[:16]}...")
EOF
```

## Troubleshooting

### Problem: Deposit Stuck in CONFIRMING

**Symptoms**: Deposit stays in CONFIRMING status, confs not updating

**Check**:
```bash
sqlite3 swapbot.db "SELECT txid, coin, confs, required_confs FROM deposits WHERE status = 'CONFIRMING';"
```

**Possible Causes**:
1. Blockchain explorer API down
2. Invalid TXID (fake transaction)
3. XMR: Not yet credited on MEXC

**Resolution**:
- Check blockchain explorer manually
- If fake: `UPDATE deposits SET status = 'PROCESSING_ERROR' WHERE txid = '...'`
- If valid: Worker will retry automatically

### Problem: TRADE_FAILED Loop

**Symptoms**: Deposit keeps retrying but failing

**Check retry count** (in logs):
```bash
grep "YOUR_TXID" /root/Convertbot/logs/worker.log | grep -c "TRADE_FAILED"
```

**Possible Causes**:
1. MEXC balance already sold (double-sell attempt)
2. API rate limiting
3. Insufficient balance

**Resolution**:
1. Check MEXC balance
2. If already sold, manually update: `UPDATE deposits SET status = 'SOLD' WHERE txid = '...'`
3. If balance exists, check MEXC API logs

### Problem: Withdrawal Failed

**Symptoms**: Status is SOLD but withdrawal not happening

**Check**:
```bash
sqlite3 swapbot.db "SELECT final_usdt, target_address FROM deposits WHERE status = 'SOLD';"
```

**Possible Causes**:
1. Not enough confirmations yet
2. MEXC withdrawal limit
3. Invalid TRC20 address

**Resolution**:
1. Check confs vs required_confs
2. Manual withdrawal if needed
3. Verify address format (starts with T, 34 chars)

### Problem: User Not Receiving Notifications

**Check**:
```bash
grep "Failed to notify" /root/Convertbot/logs/worker.log
```

**Possible Causes**:
1. User blocked the bot
2. Telegram API issues

**Resolution**: User must /start the bot again

### Problem: XMR Stuck

**Symptoms**: XMR deposit not progressing

**Check MEXC deposit history**:
```python
python3 << 'EOF'
from libs.mexc_client import MEXCClient
from app.config import settings

mexc = MEXCClient(settings.mexc_api_key, settings.mexc_api_secret)
deposits = mexc.get_deposit_history(coin="XMR", limit=20)
for d in deposits:
    print(f"Amount: {d['amount']} - Status: {d['status']} - TXID: {d.get('txId', 'N/A')}")
EOF
```

**MEXC Deposit Status Codes**:
- 1 = Pending
- 5/6 = Credited (proceed)
- 9 = Under review (wait)

**Resolution**: Wait for MEXC to credit, or contact MEXC support if stuck

## Referral System Queries

### View User's Referral Stats

```bash
sqlite3 swapbot.db "SELECT referral_code, referral_balance FROM users WHERE user_id = 123456789;"
```

### View All Referrers

```bash
sqlite3 swapbot.db "SELECT user_id, referral_code, referral_balance FROM users WHERE referral_balance > 0;"
```

### View Referral Earnings

```bash
sqlite3 swapbot.db "SELECT * FROM referral_earnings ORDER BY created_at DESC LIMIT 20;"
```

## Health Checks

### Quick System Check

```bash
#!/bin/bash
echo "=== Services ==="
systemctl is-active convertbot-bot.service
systemctl is-active convertbot-worker.service

echo "=== Database ==="
sqlite3 swapbot.db "SELECT status, COUNT(*) FROM deposits GROUP BY status;"

echo "=== Recent Activity ==="
tail -5 /root/Convertbot/logs/worker.log
```

### Check for Stuck Deposits (older than 1 hour)

```bash
sqlite3 swapbot.db "SELECT txid, coin, status, confs, datetime(inserted_at) FROM deposits WHERE status IN ('NEW', 'CONFIRMING', 'CONFIRMED', 'SOLD') AND inserted_at < datetime('now', '-1 hour');"
```

## Backup

### Backup Database

```bash
cp /root/Convertbot/swapbot.db /root/Convertbot/backups/swapbot_$(date +%Y%m%d_%H%M%S).db
```

### Export Deposits

```bash
sqlite3 swapbot.db ".mode csv" ".output deposits_backup.csv" "SELECT * FROM deposits;"
```

## i18n Verification

### Check for Hardcoded English Text

After deployment, verify no English UI text leaked into the bot:

```bash
# Should return NO matches (except coin names Bitcoin/Litecoin/Dash/Monero allowed)
grep -nE '"[^"]*Welcome[^"]*"' telegram_bot_improved.py
grep -nE '"[^"]*Invalid format[^"]*"' telegram_bot_improved.py
```

### Verify Fee Configuration

```bash
# Check fee is set correctly in config
grep -E "commission_percent|fee_fixed_usd" app/config.py

# Verify no hardcoded 3% exists
grep -rn "3%" --include="*.py" --exclude-dir=venv
grep -rn "0.03" --include="*.py" --exclude-dir=venv
```

### Test i18n Import

```bash
python3 -c "from app.i18n import MSG; print('Fee:', MSG.fee_display())"
```

### Compile Check (Pre-Deploy)

```bash
python3 -m py_compile telegram_bot_improved.py
python3 -m py_compile app/worker.py
python3 -m py_compile app/i18n/hy.py
echo "All files compile OK"
```

### Change Fee

To change the fee, edit **only** `app/config.py`:

```python
commission_percent: float = 2.0  # Change this (e.g., 3.0 for 3%)
fee_fixed_usd: float = 1.0       # Change this (e.g., 2.0 for $2)
```

All UI text will automatically update via `MSG.fee_display()`.

## Security Reminders

1. Never share `.env` file contents
2. Keep MEXC API keys secure
3. Use DRY_RUN=true for testing
4. Monitor logs for suspicious activity
5. Regular database backups
