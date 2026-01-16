# Convertbot - Project Structure

## Directory Layout

```
Convertbot/
├── .env                          # Environment variables (API keys, addresses)
├── .env.example                  # Template for .env file
├── .gitignore                    # Git ignore rules
├── requirements.txt              # Python dependencies
├── swapbot.db                    # SQLite database (not in git)
├── README.md                     # Project documentation
├── PROJECT_STRUCTURE.md          # This file
│
├── telegram_bot_improved.py      # Main Telegram bot (user interface)
│
├── app/                          # Core application logic
│   ├── __init__.py
│   ├── config.py                 # Configuration & settings from env
│   ├── db.py                     # Database operations (SQLite)
│   ├── models.py                 # Data models (Deposit, CoinType, DepositStatus, User)
│   ├── texts.py                  # Localized text strings (ASCII placeholders)
│   ├── worker.py                 # Background worker (monitors deposits)
│   ├── pipeline.py               # Trading pipeline (sell & withdraw)
│   ├── logger.py                 # Logging configuration
│   ├── validation.py             # Input validation ($20 minimum)
│   ├── blockchain_verify.py      # Blockchain verification utilities
│   ├── transaction_tracker.py    # Transaction tracking
│   ├── explorer_retry.py         # Explorer API retry logic
│   └── cleanup_manager.py        # Cleanup utilities for old deposits
│
├── libs/                         # External service clients
│   ├── __init__.py
│   ├── mexc_client.py            # MEXC exchange API (trading, withdrawals)
│   ├── mexc_deposit.py           # MEXC deposit history & verification
│   ├── explorer_client.py        # Blockchain explorers (BTC, LTC, DASH)
│   └── telegram_client.py        # Telegram notification utilities
│
├── infra/                        # Infrastructure files
│   └── db/
│       └── schema.sql            # Database schema definition
│
├── start_convertbot.sh           # Start bot & worker
├── stop_convertbot.sh            # Stop services
├── check_status.sh               # Quick status check
├── watch_logs.sh                 # Colored live logs
├── live_logs.sh                  # Alternative log monitoring
└── cleanup.sh                    # Cleanup script
```

## Component Overview

### Telegram Bot (`telegram_bot_improved.py`)

User-facing interface handling:
- Coin selection (BTC, LTC, DASH, XMR -> USDT/TRX)
- TXID collection and validation
- TRC20 address collection
- Transaction status checks
- Conversation flow management

### Worker (`app/worker.py`)

Background process that:
- Monitors pending deposits every 30 seconds
- Checks blockchain for confirmations
- Handles XMR via MEXC deposit history
- Triggers trading pipeline when confirmed
- Manages withdrawal after full confirmations
- Auto-retries TRADE_FAILED deposits (every 5 cycles)

### Pipeline (`app/pipeline.py`)

Trading execution:
- Fetches on-chain amount from blockchain/database
- Sells crypto to USDT on MEXC
- Calculates fees (3% + $1 network)
- Handles two-tier withdrawal (XMR immediate, others delayed)
- Sends user notifications

### Database (`app/db.py`)

SQLite operations:
- Deposit CRUD operations
- User management
- Referral system queries
- Status updates and tracking

### MEXC Client (`libs/mexc_client.py`)

Exchange integration:
- Account balance queries
- Market orders (BUY/SELL)
- BTC special handling (BTC -> USDC -> USDT)
- USDT/TRX withdrawals
- Deposit history for XMR verification

### Explorer Client (`libs/explorer_client.py`)

Blockchain queries:
- BTC: blockchain.info or blockchair
- LTC: blockchair
- DASH: blockchair
- Confirmation counts
- Transaction amounts

## Data Models

### DepositStatus (Enum)

```
NEW           -> Initial state
CONFIRMING    -> Waiting for confirmations
CONFIRMED     -> Ready to trade
SOLD          -> Traded, waiting for withdrawal
WITHDRAWN     -> Complete
FAILED        -> Generic failure
TRADE_FAILED  -> Trade failed (will retry)
WITHDRAWAL_FAILED
PROCESSING_ERROR -> Invalid/fake transaction
AMOUNT_TOO_SMALL -> Below $20 minimum
```

### CoinType (Enum)

```
BTC, LTC, DASH, XMR, USDT, TRX
```

### Deposit (Dataclass)

```python
txid: str
coin: CoinType
user_id: int
status: DepositStatus
confs: int
required_confs: int
target_address: str
onchain_amount: Decimal
usdt_amount: float
final_usdt: float
output_coin: str  # 'USDT' or 'TRX'
```

## Worker Cycle Flow

```
1. Fetch pending deposits (NEW, CONFIRMING, CONFIRMED, SOLD)
2. For each deposit:
   - NEW/CONFIRMING: Check blockchain confirmations
     - Fake tx detected -> PROCESSING_ERROR
     - XMR: Check MEXC deposit history
     - Enough confs -> CONFIRMED
   - CONFIRMED: Validate amount, run pipeline
     - Amount < $20 -> notify user/admin
     - Pipeline success -> SOLD or WITHDRAWN
   - SOLD: Check full confirmations
     - Ready -> withdraw USDT -> WITHDRAWN
3. Every 5th cycle: Reset TRADE_FAILED -> CONFIRMED
4. Sleep 30 seconds
5. Repeat
```

## VPS Service Structure

```
convertbot-bot.service    -> telegram_bot_improved.py
convertbot-worker.service -> python -m app.worker
```

Logs:
```
/root/Convertbot/logs/worker.log
/root/Convertbot/logs/worker-error.log
```

## Key Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| DRY_RUN | Simulation mode | true |
| COMMISSION_PERCENT | Fee percentage | 3.0 |
| required_confs_btc | BTC confirmations | 2 |
| required_confs_ltc | LTC confirmations | 4 |
| required_confs_dash | DASH confirmations | 4* |

*Note: DASH uses 12 confirmations in production (set in bot)

## Development Notes

1. Armenian text is stored on VPS only (not in git)
2. Code uses `TEXTS["key"]` for all user-facing strings
3. BTC trading goes through USDC intermediate pair
4. XMR has no public blockchain explorer - uses MEXC deposit history
5. Two-tier system: early sell for price protection, late withdrawal for security
