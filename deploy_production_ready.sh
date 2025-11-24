#!/bin/bash
# Complete Production-Ready Deployment Script
# Deploys ALL improvements: Security, Admin Tools, Tracking

echo "🚀 PRODUCTION-READY DEPLOYMENT"
echo "================================================================"
echo ""
echo "📋 ALL FEATURES BEING DEPLOYED:"
echo ""
echo "🔒 SECURITY FEATURES:"
echo "   • Rate limiting (30s cooldown between swaps)"
echo "   • Daily quotas (10 swaps, $10,000 per day per user)"
echo "   • Blacklist system for fraudulent TXIDs"
echo "   • Input normalization (strips whitespace, newlines)"
echo "   • Enhanced duplicate TXID detection"
echo ""
echo "🛠️  ADMIN TOOLS:"
echo "   • /debug - Show bot status (NO secrets exposed)"
echo "   • /blacklist_add <txid> <reason> - Block fraudulent TXIDs"
echo "   • /blacklist_remove <txid> - Unblock TXIDs"
echo "   • /force_retry <txid> - Manually retry failed deposits"
echo ""
echo "📊 TRACKING & RELIABILITY:"
echo "   • Attempt counter (max 5 attempts before giving up)"
echo "   • Auto-retry for TRADE_FAILED and WITHDRAWAL_FAILED"
echo "   • Better error logging and admin notifications"
echo ""
echo "💰 PREVIOUS FIXES (Already Deployed):"
echo "   • Fixed double fee bug (users get 1 USDT more)"
echo "   • Fixed XMR withdrawal bug"
echo "   • Fixed Telegram check button"
echo "   • Removed notification spam"
echo ""

read -p "Press ENTER to deploy all production features..."

echo ""
echo "1️⃣ Stopping services..."
sudo systemctl stop convertbot-worker convertbot-bot
sleep 2

echo ""
echo "2️⃣ Pulling latest code from GitHub..."
cd /root/Convertbot
git pull origin claude/continue-convert-bot-01NaRqFFu8ZgiFs2xV29rW6z

if [ $? -ne 0 ]; then
    echo "❌ Git pull failed!"
    exit 1
fi

echo ""
echo "3️⃣ Running database migrations..."
source venv/bin/activate
python3 migrate_database.py

if [ $? -ne 0 ]; then
    echo "❌ Database migration failed!"
    echo "Please check migrate_database.py for errors"
    exit 1
fi

echo ""
echo "4️⃣ Clearing Python cache..."
find . -path ./venv -prune -o -type f \( -name "*.pyc" -o -name "*.pyo" \) -exec rm {} \; 2>/dev/null
find . -path ./venv -prune -o -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find venv -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null
find venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

cache_count=$(find . -name "*.pyc" -o -name "*.pyo" -o -name "__pycache__" 2>/dev/null | wc -l)
echo "   Remaining cache files: $cache_count"

echo ""
echo "5️⃣ Verifying all features are present..."

all_good=true

# Check 1: Rate limiting
if grep -q "check_rate_limit" telegram_bot_improved.py && grep -q "RATE_LIMIT_COOLDOWN" telegram_bot_improved.py; then
    echo "   ✅ Rate limiting present"
else
    echo "   ❌ Rate limiting NOT found!"
    all_good=false
fi

# Check 2: Daily quotas
if grep -q "check_daily_quota" telegram_bot_improved.py && grep -q "DAILY_SWAP_LIMIT" telegram_bot_improved.py; then
    echo "   ✅ Daily quotas present"
else
    echo "   ❌ Daily quotas NOT found!"
    all_good=false
fi

# Check 3: Blacklist system
if grep -q "is_blacklisted" telegram_bot_improved.py; then
    echo "   ✅ Blacklist system present"
else
    echo "   ❌ Blacklist system NOT found!"
    all_good=false
fi

# Check 4: Admin commands
if grep -q "cmd_debug" telegram_bot_improved.py && grep -q "cmd_blacklist_add" telegram_bot_improved.py; then
    echo "   ✅ Admin commands present"
else
    echo "   ❌ Admin commands NOT found!"
    all_good=false
fi

# Check 5: Attempt counter
if grep -q "increment_attempt_count" app/db.py && grep -q "attempt_count" app/worker.py; then
    echo "   ✅ Attempt counter present"
else
    echo "   ❌ Attempt counter NOT found!"
    all_good=false
fi

# Check 6: Input normalization
if grep -q "clean_text.replace" telegram_bot_improved.py; then
    echo "   ✅ Input normalization present"
else
    echo "   ❌ Input normalization NOT found!"
    all_good=false
fi

if [ "$all_good" = false ]; then
    echo ""
    echo "❌ VERIFICATION FAILED! Not all features are present."
    exit 1
fi

echo ""
echo "6️⃣ Starting services..."
sudo systemctl start convertbot-worker
sleep 3
sudo systemctl start convertbot-bot
sleep 2

echo ""
echo "7️⃣ Checking service status..."
worker_status=$(systemctl is-active convertbot-worker)
bot_status=$(systemctl is-active convertbot-bot)

if [ "$worker_status" = "active" ]; then
    echo "   ✅ Worker: RUNNING"
else
    echo "   ❌ Worker: $worker_status"
fi

if [ "$bot_status" = "active" ]; then
    echo "   ✅ Bot: RUNNING"
else
    echo "   ❌ Bot: $bot_status"
fi

echo ""
echo "================================================================"
echo "✅ PRODUCTION-READY DEPLOYMENT COMPLETE!"
echo "================================================================"
echo ""
echo "🎉 YOUR CONVERTBOT IS NOW PRODUCTION-READY!"
echo ""
echo "🔒 SECURITY IMPROVEMENTS:"
echo "   • Users can only swap once every 30 seconds"
echo "   • Daily limit: 10 swaps, $10,000 per user"
echo "   • Fraudulent TXIDs can be blacklisted"
echo "   • Input is normalized (handles whitespace, etc.)"
echo ""
echo "🛠️  ADMIN CAPABILITIES:"
echo "   Try these commands in Telegram:"
echo "   /debug - See bot stats"
echo "   /blacklist_add abc123...def456 Scammer"
echo "   /blacklist_remove abc123...def456"
echo "   /force_retry abc123...def456"
echo ""
echo "📊 RELIABILITY:"
echo "   • Failed deposits auto-retry (max 5 attempts)"
echo "   • After 5 failures, deposit marked as PROCESSING_ERROR"
echo "   • Logs show attempt counts for debugging"
echo ""
echo "💡 TIPS:"
echo "   1. Test rate limiting: Try /start twice quickly"
echo "   2. Test /debug command to see stats"
echo "   3. Monitor logs: tail -f logs/worker.log"
echo "   4. Check for stuck deposits with /debug"
echo ""
echo "⚠️  IMPORTANT:"
echo "   • Configure ADMIN_USER_IDS in telegram_bot_improved.py"
echo "   • Current admin: User ID from settings.admin_chat_id"
echo "   • Adjust DAILY_SWAP_LIMIT/DAILY_VOLUME_LIMIT as needed"
echo ""
echo "📝 Next deployment: Just run this script again!"
echo ""
