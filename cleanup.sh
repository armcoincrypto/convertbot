#!/bin/bash
echo "🧹 CLEANING UP PROJECT..."

# 1. Remove backup files
echo "Removing backup files..."
rm -f app/worker.py.backup app/worker.py.bak app/worker.py.bak2
rm -f libs/explorer_client.py.old
rm -f libs/mexc_client.py.backup

# 2. Remove swap files
echo "Removing swap files..."
rm -f .telegram_bot_improved.py.swo .telegram_bot_improved.py.swp

# 3. Remove old markdown docs
echo "Removing old documentation..."
rm -f BTC_TRADING_ISSUE.md FINAL_STATUS_NOV4.md PRODUCTION_READY.md
rm -f SESSION_COMPLETE_NOV_3.md SYSTEM_READY_NOV_3.md SYSTEM_STATUS.md TEST_ALL_PAIRS.md

# 4. Remove test files
echo "Removing test files..."
rm -f test_bot_simple.py check_health.py
rm -rf tests/

# 5. Remove old scripts
echo "Removing old scripts..."
rm -f add_sold_and_xmr.py add_test_deposit.py add_worker_logic.py add_xmr_support.py
rm -f implement_two_tier.py manual_fix_transaction.py cleanup_invalid.py
rm -f run_worker.sh start_bot.sh monitor.sh errors_only.sh success_only.sh cleanup_stuck.sh

# 6. Remove duplicate database
echo "Removing duplicate database..."
rm -f convertbot.db

# 7. Remove old directories
echo "Removing old directories..."
rm -rf swapbot/ functions/

# 8. Remove IDE files
echo "Removing IDE files..."
rm -rf .idea/ .pytest_cache/ __pycache__/

# 9. Remove temp files
rm -f cleanup_plan.txt .env.local

echo ""
echo "✅ CLEANUP COMPLETE!"
echo ""
echo "📂 REMAINING STRUCTURE:"
find . -maxdepth 2 -type f ! -path "./venv/*" ! -path "./.git/*" | sort
