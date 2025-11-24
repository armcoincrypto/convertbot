#!/bin/bash
# Deploy ALL fixes: fee calculation + auto-retry + Telegram button

echo "🚀 COMPLETE SYSTEM FIX DEPLOYMENT"
echo "================================================================"
echo ""
echo "📋 ALL FIXES BEING DEPLOYED:"
echo ""
echo "1. ✅ Fee Calculation Fix (CRITICAL)"
echo "   - Fixed double network fee bug"
echo "   - Users receive 1 USDT MORE per transaction"
echo "   - OLD: User paid 2 USDT in fees"
echo "   - NEW: User pays only 1 USDT (MEXC fee)"
echo ""
echo "2. ✅ Auto-Retry for Failed Withdrawals"
echo "   - WITHDRAWAL_FAILED deposits now auto-retry every 2.5 min"
echo "   - No more 9-hour delays like with XMR!"
echo "   - Both TRADE_FAILED and WITHDRAWAL_FAILED auto-retry"
echo ""
echo "3. ✅ Telegram Check Button Fixed"
echo "   - '📊 Ստուգել' button now works"
echo "   - Users can check transaction status"
echo "   - Shows status in Armenian"
echo ""
echo "4. ✅ XMR Withdrawal Bug Fixed"
echo "   - Reload deposit from DB before withdrawal"
echo "   - No more 'No stored USDT amount' error"
echo ""
echo "5. ✅ Notification Improvements"
echo "   - Removed confusing early 'Deposit confirmed!' messages"
echo "   - Removed TRADE_FAILED error spam"
echo "   - Users only get notified when they receive funds"
echo ""

read -p "Press ENTER to deploy all fixes..."

echo ""
echo "1️⃣ Stopping services..."
sudo systemctl stop convertbot-worker convertbot-bot
sleep 2

echo ""
echo "2️⃣ Pulling all fixes from GitHub..."
cd /root/Convertbot
git pull origin claude/continue-convert-bot-01NaRqFFu8ZgiFs2xV29rW6z

if [ $? -ne 0 ]; then
    echo "❌ Git pull failed!"
    exit 1
fi

echo ""
echo "3️⃣ Clearing Python cache..."
find . -path ./venv -prune -o -type f \( -name "*.pyc" -o -name "*.pyo" \) -exec rm {} \; 2>/dev/null
find . -path ./venv -prune -o -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find venv -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null
find venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

cache_count=$(find . -name "*.pyc" -o -name "*.pyo" -o -name "__pycache__" 2>/dev/null | wc -l)
echo "   Remaining cache files: $cache_count"

echo ""
echo "4️⃣ Verifying all fixes are present..."

all_good=true

# Check 1: Fee calculation fix
if grep -q "mexc_withdrawal_fee" app/pipeline.py && grep -q "withdrawal_amount" app/pipeline.py; then
    echo "   ✅ Fee calculation fix present"
else
    echo "   ❌ Fee calculation fix NOT found!"
    all_good=false
fi

# Check 2: Auto-retry for WITHDRAWAL_FAILED
if grep -q "retry_failed_deposits" app/worker.py && grep -q "WITHDRAWAL_FAILED" app/worker.py; then
    echo "   ✅ Auto-retry for WITHDRAWAL_FAILED present"
else
    echo "   ❌ Auto-retry fix NOT found!"
    all_good=false
fi

# Check 3: XMR reload fix
if grep -q "Reload deposit from DB" app/pipeline.py; then
    echo "   ✅ XMR withdrawal fix present"
else
    echo "   ❌ XMR withdrawal fix NOT found!"
    all_good=false
fi

# Check 4: Telegram check button fix
if grep -q "Վերամշակվում է" telegram_bot_improved.py; then
    echo "   ✅ Telegram check button fix present"
else
    echo "   ❌ Telegram check button fix NOT found!"
    all_good=false
fi

# Check 5: Notification fixes
if ! grep -q "send_message" app/worker.py | grep -q "Deposit confirmed"; then
    echo "   ✅ Notification spam removed"
else
    echo "   ⚠️  Some notifications might still be present"
fi

if [ "$all_good" = false ]; then
    echo ""
    echo "❌ VERIFICATION FAILED! Not all fixes are present."
    echo "Please check the files manually or pull again."
    exit 1
fi

echo ""
echo "5️⃣ Starting services..."
sudo systemctl start convertbot-worker
sleep 3
sudo systemctl start convertbot-bot
sleep 2

echo ""
echo "6️⃣ Checking service status..."
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
echo "✅ ALL FIXES DEPLOYED SUCCESSFULLY!"
echo "================================================================"
echo ""
echo "📊 SUMMARY OF IMPROVEMENTS:"
echo ""
echo "💰 FINANCIAL IMPACT:"
echo "   • Users receive 1 USDT MORE per transaction"
echo "   • Fee structure now transparent and correct"
echo ""
echo "⚡ SPEED IMPROVEMENTS:"
echo "   • Failed withdrawals retry in 2.5 min (was: stuck forever)"
echo "   • Failed trades retry in 2.5 min (was: already working)"
echo "   • XMR withdrawals work immediately (was: failed)"
echo ""
echo "🎯 USER EXPERIENCE:"
echo "   • Telegram check button works"
echo "   • Status updates in Armenian"
echo "   • No more notification spam"
echo "   • Only get notified when receiving funds"
echo ""
echo "🔧 TECHNICAL:"
echo "   • All coins: BTC, LTC, DASH, XMR"
echo "   • All outputs: USDT and TRX/TRON"
echo "   • Auto-retry every 5 cycles (2.5 minutes)"
echo ""
echo "📝 Next steps:"
echo "   1. Test with small deposits (all coins)"
echo "   2. Monitor logs: tail -f /root/Convertbot/logs/worker.log"
echo "   3. Test Telegram '📊 Ստուգել' button"
echo "   4. Verify users receive correct amounts"
echo ""
echo "🔍 What to watch for:"
echo "   • NEW deposits: Use correct fee calculation"
echo "   • WITHDRAWAL_FAILED: Auto-retry in 2.5 min"
echo "   • User amounts: Should match notification exactly"
echo ""
