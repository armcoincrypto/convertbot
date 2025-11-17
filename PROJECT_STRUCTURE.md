# 🎯 Convertbot - Production Structure

## Core Files
```
Convertbot/
├── .env                          # Environment variables (API keys)
├── requirements.txt              # Python dependencies
├── swapbot.db                    # SQLite database (deposits & transactions)
├── telegram_bot_improved.py      # Main Telegram bot
├── README.md                     # Project documentation
│
├── app/                          # Core application logic
│   ├── config.py                 # Configuration & settings
│   ├── db.py                     # Database operations
│   ├── models.py                 # Data models (Deposit, CoinType, etc)
│   ├── worker.py                 # Main worker (monitors deposits)
│   ├── pipeline.py               # Trading pipeline (sell & withdraw)
│   ├── logger.py                 # Logging configuration
│   ├── validation.py             # Input validation
│   ├── blockchain_verify.py      # Blockchain verification
│   ├── transaction_tracker.py    # Transaction tracking
│   ├── explorer_retry.py         # Explorer API retry logic
│   └── cleanup_manager.py        # Cleanup utilities
│
├── libs/                         # External service clients
│   ├── mexc_client.py            # MEXC exchange API
│   ├── explorer_client.py        # Blockchain explorers
│   ├── telegram_client.py        # Telegram utilities
│   └── mexc_deposit.py           # MEXC deposit tracking
│
├── Scripts/                      # Management scripts
│   ├── start_convertbot.sh       # Start bot & worker
│   ├── stop_convertbot.sh        # Stop services
│   ├── check_status.sh           # Quick status check
│   ├── watch_logs.sh             # Colored live logs
│   └── live_logs.sh              # Live monitoring
│
└── Logs/
    ├── worker.log                # Worker activity log
    └── bot.log                   # Telegram bot log
```

## Supported Coins
- ✅ BTC: 2 confirmations
- ✅ LTC: 4 confirmations  
- ✅ DASH: 12 confirmations
- ✅ XMR: MEXC deposit history (instant)

## Workflow
1. User deposits crypto → Bot detects on blockchain
2. Confirmations reach threshold → Sell on MEXC
3. Get USDT → Withdraw to user's TRC20 address
4. User receives USDT (minus 3% commission + $1 network fee)

## Key Features
- Two-tier system (early sell, late withdraw)
- Auto-retry for MEXC delays
- Persistent storage (survives restarts)
- Comprehensive logging
- 24 successful withdrawals completed ✅
