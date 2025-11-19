# VPS Deployment Guide for Convertbot

## Current Status
✅ All files transferred to VPS (207.180.212.142)
✅ Virtual environment created
✅ Dependencies installed
✅ Database initialized
✅ Worker tested and working

## Next Steps

### 1. Set Up Worker as System Service (24/7 Operation)

On your VPS, run these commands:

```bash
cd /root/Convertbot
sudo bash setup_service.sh
```

This will:
- Create a systemd service that runs the worker automatically
- Enable auto-start on VPS reboot
- Set up logging to `/root/Convertbot/logs/`
- Start the worker immediately

### 2. Add VPS IP to MEXC API Whitelist

**IMPORTANT**: You MUST do this or trades/withdrawals will fail!

1. Go to https://www.mexc.com/
2. Log in to your account
3. Navigate to: **Account → API Management**
4. Find your API key: `mx0vgl70jrXIxXQdn2`
5. Click **Edit** or **Manage**
6. Under **IP Whitelist**, add: `207.180.212.142`
7. Save changes

### 3. Verify Everything Works

Check worker status:
```bash
sudo systemctl status convertbot-worker
```

View live logs:
```bash
sudo journalctl -u convertbot-worker -f
```

Or view worker output file:
```bash
tail -f /root/Convertbot/logs/worker.log
```

### 4. Test with Real Deposit

Send a small test deposit to one of your addresses:
- BTC: `33vFCeDJXdEPTnWFEyy5tRy85iQo1oBtw4`
- LTC: `ltc1qdx26fhhma5x0kwld5l0dxrwc0mrcygl6fnvnxp`
- DASH: `Xdiuzho4EhWWzEEDbNzbxYpt55DRDETgD9`
- XMR: `88jVTyDDAJzWyaamiGWaAyXn487o53v7hgzPY46qAwBEBCJsvXoBVadgq1yj7kuBrD6sKo3v49twPCtJ5vozbTqW3HMqWb7`

Then insert to database:
```bash
cd /root/Convertbot
source venv/bin/activate
python insert_deposit.py
```

Watch logs to see it process:
```bash
tail -f /root/Convertbot/logs/worker.log
```

## Useful Commands

### Service Management
```bash
sudo systemctl status convertbot-worker   # Check status
sudo systemctl stop convertbot-worker     # Stop service
sudo systemctl start convertbot-worker    # Start service
sudo systemctl restart convertbot-worker  # Restart service
sudo systemctl disable convertbot-worker  # Disable auto-start
sudo systemctl enable convertbot-worker   # Enable auto-start
```

### View Logs
```bash
# Live system logs
sudo journalctl -u convertbot-worker -f

# Worker output log
tail -f /root/Convertbot/logs/worker.log

# Worker error log
tail -f /root/Convertbot/logs/worker-error.log

# Last 100 lines
sudo journalctl -u convertbot-worker -n 100
```

### Database Operations
```bash
cd /root/Convertbot
source venv/bin/activate

# Check deposits
python check_deposits.py

# Verify specific deposit
python verify_deposit_status.py

# Insert test deposit
python insert_deposit.py
```

### Update Code from GitHub
```bash
cd /root/Convertbot
git pull origin claude/fix-pending-deposits-error-0191kMkiRXVQ6ccEqu7DZHUz
sudo systemctl restart convertbot-worker
```

## Troubleshooting

### Worker not starting?
```bash
sudo journalctl -u convertbot-worker -n 50
```

### Check if worker process is running
```bash
ps aux | grep worker
```

### Manual test (without service)
```bash
cd /root/Convertbot
source venv/bin/activate
python -m app.worker
```

### MEXC API errors?
1. Verify IP 207.180.212.142 is in whitelist
2. Check API key has withdrawal permissions
3. Verify API secret is correct in `.env`

### Database locked errors?
```bash
# Stop service first
sudo systemctl stop convertbot-worker

# Then run manual operations
python check_deposits.py

# Restart service
sudo systemctl start convertbot-worker
```

## File Locations

- **Service file**: `/etc/systemd/system/convertbot-worker.service`
- **Worker code**: `/root/Convertbot/`
- **Logs**: `/root/Convertbot/logs/`
- **Database**: `/root/Convertbot/swapbot.db`
- **Config**: `/root/Convertbot/.env`
- **Virtual env**: `/root/Convertbot/venv/`

## Security Notes

- ✅ API keys stored in `.env` file (not committed to GitHub)
- ✅ Worker runs as root (required for systemd service)
- ✅ IP whitelist enabled on MEXC (only VPS can use API)
- ⚠️  Make sure `.env` file permissions are secure: `chmod 600 .env`

## Current Configuration

**VPS**: 207.180.212.142
**Worker**: Runs every 30 seconds
**Status**: Active and monitoring for deposits

**Addresses Being Monitored**:
- BTC: 33vFCeDJXdEPTnWFEyy5tRy85iQo1oBtw4
- LTC: ltc1qdx26fhhma5x0kwld5l0dxrwc0mrcygl6fnvnxp
- DASH: Xdiuzho4EhWWzEEDbNzbxYpt55DRDETgD9
- XMR: 88jVTyDDAJzWyaamiGWaAyXn487o53v7hgzPY46qAwBEBCJsvXoBVadgq1yj7kuBrD6sKo3v49twPCtJ5vozbTqW3HMqWb7

**Required Confirmations**:
- BTC: 2 confirmations (early sell) → 6 confirmations (withdrawal)
- LTC: 4 confirmations (early sell) → 12 confirmations (withdrawal)
- DASH: 2 confirmations (early sell) → 6 confirmations (withdrawal)
- XMR: 10 confirmations on MEXC (immediate withdrawal after deposit detected)

---

## All Fixes Applied

1. ✅ Fixed database row.get() errors
2. ✅ Fixed infinite retry loop for small amounts
3. ✅ Fixed withdrawal success detection
4. ✅ Fixed XMR deposit detection (enum comparison)
5. ✅ Updated notifications to Armenian
6. ✅ Deployed to VPS with static IP
7. ✅ Set up as systemd service for 24/7 operation
