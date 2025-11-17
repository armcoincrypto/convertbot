# 🪙 Convertbot - Cryptocurrency Conversion Service

Automated cryptocurrency conversion bot that accepts deposits in BTC, LTC, DASH, and XMR, converts them to USDT on MEXC exchange, and withdraws to users' TRC20 addresses.

## 🌟 Features

- ✅ **Multi-coin support**: BTC, LTC, DASH, XMR
- ✅ **Automated trading**: Sells crypto → USDT on MEXC
- ✅ **Two-tier system**: Early sell for price protection, late withdrawal for security
- ✅ **Auto-retry**: Automatically retries failed trades every 2.5 minutes
- ✅ **Telegram bot**: User-friendly interface with Armenian language support
- ✅ **Blockchain monitoring**: Real-time confirmation tracking
- ✅ **Smart error handling**: Graceful degradation and automatic recovery

## 📊 Statistics

- **Successful withdrawals**: 24+
- **Supported coins**: 4 (BTC, LTC, DASH, XMR)
- **Average processing time**: 5-15 minutes
- **Fee structure**: 3% commission + $1 network fee

## 🏗️ Architecture
```
Convertbot/
├── app/
│   ├── worker.py          # Background worker (monitors deposits)
│   ├── pipeline.py        # Trading pipeline (sell & withdraw)
│   ├── db.py              # Database operations
│   ├── models.py          # Data models
│   ├── config.py          # Configuration management
│   ├── logger.py          # Logging setup
│   └── validation.py      # Amount validation
├── libs/
│   ├── mexc_client.py     # MEXC exchange integration
│   ├── explorer_client.py # Blockchain explorer API client
│   └── telegram_client.py # Telegram utilities
├── telegram_bot_improved.py  # Main Telegram bot interface
├── .env                   # Environment variables (not in git)
└── requirements.txt       # Python dependencies
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- MEXC exchange account with API keys
- Telegram bot token
- VPS (recommended for 24/7 operation)

### Installation
```bash
# Clone repository
git clone https://github.com/yourusername/convertbot.git
cd convertbot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and addresses
nano .env
```

### Configuration

Edit `.env` file:
```env
MEXC_API_KEY=your_mexc_api_key
MEXC_API_SECRET=your_mexc_secret
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_CHAT_ID=your_telegram_id
ADDR_BTC=your_btc_deposit_address
ADDR_LTC=your_ltc_deposit_address
ADDR_DASH=your_dash_deposit_address
ADDR_XMR=your_xmr_deposit_address
DRY_RUN=false  # Set to true for testing
```

### Running
```bash
# Start services
./start_convertbot.sh

# Stop services
./stop_convertbot.sh

# Monitor logs
./watch_logs.sh
# or
tail -f worker.log
tail -f bot.log
```

## 📋 How It Works

### 1. User Flow
```
User → /start → Gets deposit addresses
     → Sends crypto to address
     → Bot detects deposit
     → Waits for confirmations
     → Sells crypto → USDT
     → Withdraws USDT to user's TRC20 address
```

### 2. Two-Tier System

**Early Sell (Price Protection)**:
- BTC/LTC: Sells at 2 confirmations
- DASH: Sells at 12 confirmations
- Locks in price early to avoid volatility

**Late Withdrawal (Security)**:
- Waits for full confirmations
- BTC: 2 confirmations
- LTC: 4 confirmations
- DASH: 12 confirmations
- XMR: 10+ confirmations (via MEXC deposit history)

### 3. Confirmation Requirements

| Coin | Min Confs | Full Confs | Method |
|------|-----------|------------|--------|
| BTC  | 2         | 2          | Blockchain explorer |
| LTC  | 2         | 4          | Blockchain explorer |
| DASH | 12        | 12         | Blockchain explorer |
| XMR  | N/A       | 10+        | MEXC deposit history |

### 4. Fee Structure

- **Commission**: 3% of USDT value
- **Network fee**: $1 (TRC20 withdrawal)
- **Example**: $100 deposit → $97 after commission → $96 final

## 🔄 Auto-Retry System

The worker automatically retries failed trades every 5 cycles (2.5 minutes):
```python
# Cycle #5, #10, #15, etc.
🔄 Checking for TRADE_FAILED deposits to retry...
🔁 Found X TRADE_FAILED deposits, resetting to CONFIRMED...
✅ Reset X deposits to CONFIRMED for retry
```

## 🛠️ Management Scripts
```bash
./start_convertbot.sh     # Start bot + worker
./stop_convertbot.sh      # Stop services
./check_status.sh         # Quick status check
./watch_logs.sh           # Colored live monitoring
./live_logs.sh            # Alternative monitoring
```

## 📊 Database Schema
```sql
CREATE TABLE deposits (
    txid TEXT PRIMARY KEY,
    coin TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    status TEXT DEFAULT 'NEW',
    confs INTEGER DEFAULT 0,
    required_confs INTEGER,
    target_address TEXT,
    onchain_amount REAL,
    usdt_amount REAL,
    final_usdt REAL,
    inserted_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### Deposit Status Flow
```
NEW → CONFIRMING → CONFIRMED → SOLD → WITHDRAWN
                              ↓
                         TRADE_FAILED (auto-retry)
```

## 🔍 Monitoring

### Check Database Status
```bash
sqlite3 swapbot.db "SELECT status, COUNT(*) FROM deposits GROUP BY status;"
```

### View Recent Deposits
```bash
sqlite3 swapbot.db "SELECT substr(txid,1,16), coin, status, confs FROM deposits ORDER BY inserted_at DESC LIMIT 10;"
```

## ⚙️ Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `DRY_RUN` | Test mode (no real transactions) | `true` |
| `COMMISSION_PERCENT` | Commission percentage | `3.0` |
| `DATABASE_URL` | SQLite database path | `sqlite:///swapbot.db` |

## 🚨 Error Handling

- **TRADE_FAILED**: Auto-retry every 2.5 minutes
- **Blockchain API down**: Multi-provider fallback
- **MEXC API errors**: Exponential backoff retry
- **Small amounts**: Notify user to contact operator

## 📝 Logging

Structured logs with:
- ✅ Timestamp and level
- ✅ Mode indicator (DRY_RUN/LIVE)
- ✅ Detailed error messages
- ✅ Transaction tracking

Example:
```
2025-11-18 02:08:24,484 - __main__ - INFO - 🔄 Starting worker cycle #5
2025-11-18 02:08:24,484 - __main__ - INFO - Mode: LIVE
2025-11-18 02:08:24,485 - __main__ - INFO - 📊 Found 6 pending deposits
```

## 🔐 Security

- ✅ API keys in `.env` (not in git)
- ✅ Database not committed
- ✅ Logs exclude sensitive data
- ✅ DRY_RUN mode for testing
- ✅ Amount validation ($20 minimum)

## 📦 Dependencies

See `requirements.txt`:
- `aiogram` - Telegram bot framework
- `aiosqlite` - Async SQLite
- `pydantic-settings` - Configuration management
- `requests` - HTTP client for APIs

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly (use DRY_RUN=true)
5. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details

## ⚠️ Disclaimer

This bot handles real money transactions. Use at your own risk. Always:
- Test thoroughly in DRY_RUN mode first
- Start with small amounts
- Monitor logs closely
- Keep backups of your database
- Secure your API keys

## 📞 Support

- Telegram: @Conodoperatorbot
- Issues: GitHub Issues page

## 🎯 Roadmap

- [ ] Web dashboard for monitoring
- [ ] More coins (SOL, USDC, etc.)
- [ ] Multiple exchange support
- [ ] Rate limiting and throttling
- [ ] Enhanced analytics

---

**Status**: ✅ Production Ready  
**Version**: 1.0.0  
**Last Updated**: November 2024
