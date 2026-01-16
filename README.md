# Convertbot - Cryptocurrency Conversion Service

Automated Telegram cryptocurrency conversion bot that accepts deposits in BTC, LTC, DASH, and XMR, converts them to USDT (TRC20) or TRX on MEXC exchange, and withdraws to users' TRC20 addresses.

## Overview

- **Repository**: armcoincrypto/convertbot
- **VPS Path**: `/root/Convertbot`
- **Database**: SQLite at `/root/Convertbot/swapbot.db`

## Features

- Multi-coin support: BTC, LTC, DASH, XMR
- Automated trading on MEXC exchange
- Two-tier system: Early sell for price protection, late withdrawal for security
- Auto-retry for failed trades (up to 5 retries)
- Telegram bot with Armenian language support
- Blockchain monitoring with real-time confirmation tracking
- Referral system with milestone bonuses

## Architecture

### Core Files

| File | Purpose |
|------|---------|
| `telegram_bot_improved.py` | Main Telegram bot - handles user interaction |
| `app/worker.py` | Background worker - monitors deposits, executes trades |
| `app/pipeline.py` | Trading pipeline - sells crypto, withdraws USDT |
| `app/db.py` | Database operations + referral system |
| `app/texts.py` | Localized text strings (ASCII-only, Armenian added on VPS) |
| `app/config.py` | Settings from environment variables |
| `app/models.py` | Data models (Deposit, CoinType, DepositStatus) |
| `libs/mexc_client.py` | MEXC exchange API client |
| `libs/telegram_client.py` | Telegram notification client |
| `libs/explorer_client.py` | Blockchain explorer client |

### Services (systemd)

```
convertbot-bot.service    # Telegram bot UI
convertbot-worker.service # Background processor
```

### Logs

```
/root/Convertbot/logs/worker.log
/root/Convertbot/logs/worker-error.log
```

## Deposit Flow

```
NEW -> CONFIRMING -> CONFIRMED -> SOLD -> WITHDRAWN
```

| Status | Description |
|--------|-------------|
| NEW | User submits TXID |
| CONFIRMING | Waiting for blockchain confirmations |
| CONFIRMED | Enough confirmations + verified on MEXC -> sell crypto |
| SOLD | Crypto sold, waiting for full confirmations before withdrawal |
| WITHDRAWN | USDT sent to user |

### Error States

| Status | Description |
|--------|-------------|
| PROCESSING_ERROR | Fake/invalid transaction |
| TRADE_FAILED | Trade failed (retried up to 5 times) |
| AMOUNT_TOO_SMALL | Below $20 minimum |

## Supported Pairs

| Coin | Output | Confirmations | Early Sell | Notes |
|------|--------|---------------|------------|-------|
| BTC | USDT | 2 | 2 | Via USDC intermediate |
| LTC | USDT | 4 | 2 | Direct pair |
| DASH | USDT | 12 | 7 | Direct pair |
| DASH | TRX | 12 | 7 | Via USDT intermediate |
| XMR | USDT | 10 | N/A | Uses MEXC deposit history |

## Fee Structure

- **Commission**: 3%
- **Network fee**: $1 (TRC20 withdrawal)
- **Minimum deposit**: $20 USD equivalent

Example: $100 deposit -> $97 after commission -> $96 final

## Referral System

- Users get unique referral code (e.g., `REF12345678`)
- Referrer earns 30% of bot's fee on each swap
- Milestone bonuses: +$50 at 50 referrals, +$200 at 200 referrals
- Minimum withdrawal: $10

### Referral Database Columns (users table)

| Column | Description |
|--------|-------------|
| referral_code | User's unique code |
| referred_by | ID of referrer |
| referral_balance | Accumulated earnings |

### Referral Tables

- `referral_earnings` - Transaction log
- `referral_bonuses` - Claimed bonuses

## Bot Commands

| Command | Description |
|---------|-------------|
| /start | Start new exchange |
| /status | Check transaction status |
| /check | Same as /status |
| /referral | View referral stats and link |
| /withdraw | Withdraw referral earnings |
| /help | Show help |
| /operator | Contact support (@Conodoperatorbot) |

## Configuration

### Environment Variables (.env)

```env
TELEGRAM_BOT_TOKEN=your_bot_token
MEXC_API_KEY=your_mexc_api_key
MEXC_API_SECRET=your_mexc_api_secret
ADMIN_CHAT_ID=your_telegram_id
ADDR_BTC=your_btc_deposit_address
ADDR_LTC=your_ltc_deposit_address
ADDR_DASH=your_dash_deposit_address
ADDR_XMR=your_xmr_deposit_address
COMMISSION_PERCENT=3
DRY_RUN=false
```

## Database Schema

### deposits table

```sql
CREATE TABLE deposits (
    txid TEXT PRIMARY KEY,
    coin TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    status TEXT DEFAULT 'NEW',
    confs INTEGER DEFAULT 0,
    required_confs INTEGER,
    onchain_amount REAL,
    usdt_amount REAL,
    final_usdt REAL,
    target_address TEXT,
    output_coin TEXT,  -- 'USDT' or 'TRX'
    inserted_at DATETIME,
    updated_at DATETIME
);
```

### users table

```sql
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    usdt_trc20_address TEXT,
    referral_code TEXT UNIQUE,
    referred_by INTEGER,
    referral_balance REAL DEFAULT 0
);
```

## Critical Fixes Applied

### 1. Rate Limiting for Error Notifications

**Problem**: User received error message every minute for stuck deposits.

**Solution**: Added 1-hour cooldown per TXID in `_notify_error()` and `should_send_error_notification()`.

### 2. TRADE_FAILED Retry Limits

**Problem**: Infinite retries when MEXC had deposit but balance was already sold.

**Solution**:
- Max 5 retries (`MAX_TRADE_RETRIES = 5`)
- Balance check before retrying (`mexc.check_coin_balance()`)
- Admin notification after max retries

### 3. MEXC Deposit Verification

**Problem**: Bot tried to sell before MEXC credited the deposit.

**Solution**: `verify_deposit_on_mexc()` checks MEXC deposit history:
- Status 5/6 = credited (proceed)
- Status 9 = under review (wait)
- Status 1 = pending (wait)

### 4. Armenian Text Corruption

**Problem**: Claude corrupts Armenian text to "delays delays delays".

**Solution**:
- `app/texts.py` contains ASCII-only placeholders
- Armenian text added directly on VPS via nano
- Code references `TEXTS["key"]` only

## TEXTS Architecture

```python
TEXTS = {
    "error_generic": "...",       # Generic error to user
    "error_fake_tx": "...",       # Invalid transaction
    "error_amount_small": "...",  # Below minimum
    "success_withdrawal": "...",  # Withdrawal complete
    "admin_manual_fix": "...",    # Admin alert
    "admin_small_amount": "...",  # Admin: small deposit
}
```

Format placeholders: `{txid}`, `{error}`, `{amount}`, `{coin}`, `{address}`, `{wid}`, `{error_msg}`, `{user_id}`, `{usd_val}`

## Installation

```bash
# Clone repository
git clone https://github.com/armcoincrypto/convertbot.git
cd convertbot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit with your API keys
```

## Running Locally

```bash
# Start services
./start_convertbot.sh

# Stop services
./stop_convertbot.sh

# Monitor logs
./watch_logs.sh
```

## VPS Deployment

### Deploy Changes

```bash
cd /root/Convertbot
git fetch origin <branch>
git reset --hard origin/<branch>
systemctl restart convertbot-worker.service convertbot-bot.service
```

### Check Status

```bash
systemctl status convertbot-worker.service convertbot-bot.service
tail -f /root/Convertbot/logs/worker.log
sqlite3 swapbot.db "SELECT status, COUNT(*) FROM deposits GROUP BY status;"
```

### Manual USDT Withdrawal (if needed)

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

asyncio.run(manual_withdraw())
EOF
```

## Dependencies

See `requirements.txt`:
- `aiogram` - Telegram bot framework
- `aiosqlite` - Async SQLite
- `pydantic-settings` - Configuration management
- `requests` - HTTP client for APIs

## Security Notes

- API keys stored in `.env` (not in git)
- Database not committed to repository
- Logs exclude sensitive data
- DRY_RUN mode available for testing
- Amount validation enforces $20 minimum

## Important Rules for Development

1. **NEVER** output Armenian text in code - always use `TEXTS["key"]` references
2. **NEVER** modify text values in code - only add keys or logic
3. **ALWAYS** verify MEXC deposit status before trading
4. **ALWAYS** check balance before selling
5. Rate limit all error notifications (1 hour cooldown)
6. Max 5 retries for failed trades

## Support

- Telegram: @Conodoperatorbot
- Issues: GitHub Issues page

---

**Status**: Production Ready
**Version**: 1.0.0
**Last Updated**: January 2026
