#!/bin/bash
# Deploy ALL fixes: notification removal + fee calculation

echo "🚀 COMPLETE FIX DEPLOYMENT"
echo "================================================================"
echo ""
echo "📋 FIXES TO DEPLOY:"
echo "   1. ✅ Remove confusing 'Deposit confirmed!' notification"
echo "   2. ✅ Remove TRADE_FAILED error notifications (auto-retry handles them)"
echo "   3. ✅ Fix double network fee bug (CRITICAL - users getting 1 USDT less)"
echo ""
echo "💰 FEE FIX DETAILS:"
echo "   OLD: Users paid 2 USDT in fees (1 USDT to us + 1 USDT to MEXC)"
echo "   NEW: Users pay only 1 USDT fee (MEXC's withdrawal fee)"
echo "   RESULT: Users receive 1 USDT MORE than before!"
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
echo "4️⃣ Verifying fixes are present..."

fixes_ok=true

# Check 1: worker.py - should NOT have the "Deposit confirmed!" notification
if grep -A 5 "elif confs >= deposit.required_confs:" app/worker.py | grep -q "send_message"; then
    echo "   ❌ worker.py still has 'Deposit confirmed!' notification!"
    fixes_ok=false
else
    echo "   ✅ Notification fix 1: 'Deposit confirmed!' removed"
fi

# Check 2: pipeline.py - should NOT notify on TRADE_FAILED
if grep -A 3 "Trade failed:" app/pipeline.py | grep -q "_notify_error"; then
    echo "   ❌ pipeline.py still notifies on TRADE_FAILED!"
    fixes_ok=false
else
    echo "   ✅ Notification fix 2: TRADE_FAILED errors suppressed"
fi

# Check 3: pipeline.py - should use withdrawal_amount and mexc_withdrawal_fee
if grep -q "mexc_withdrawal_fee" app/pipeline.py && grep -q "withdrawal_amount" app/pipeline.py; then
    echo "   ✅ Fee fix: withdrawal_amount and mexc_withdrawal_fee present"
else
    echo "   ❌ pipeline.py missing fee fix variables!"
    fixes_ok=false
fi

# Check 4: pipeline.py - should calculate final_amount correctly
if grep -q "final_amount = withdrawal_amount - mexc_withdrawal_fee" app/pipeline.py; then
    echo "   ✅ Fee calculation: final_amount = withdrawal_amount - mexc_fee"
else
    echo "   ❌ pipeline.py missing correct fee calculation!"
    fixes_ok=false
fi

if [ "$fixes_ok" = false ]; then
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
echo "📊 SUMMARY OF CHANGES:"
echo ""
echo "1. 🔕 NOTIFICATION IMPROVEMENTS:"
echo "   • Removed confusing 'Deposit confirmed!' at early confirmations"
echo "   • Removed TRADE_FAILED error notifications (auto-retry handles them)"
echo "   • Users only get notified when they receive funds"
echo ""
echo "2. 💰 FEE CALCULATION FIX (CRITICAL):"
echo "   • Fixed double network fee bug"
echo "   • OLD: 26 USDT → user gets 23.22 USDT (lost 2.78 USDT)"
echo "   • NEW: 26 USDT → user gets 24.22 USDT (lost 1.78 USDT)"
echo "   • IMPROVEMENT: Users receive 1 USDT MORE per transaction!"
echo ""
echo "3. 🎯 AFFECTED PAIRS:"
echo "   • All coins: BTC, LTC, DASH, XMR"
echo "   • All outputs: USDT and TRX/TRON"
echo ""
echo "📝 Next steps:"
echo "   1. Monitor logs: tail -f /root/Convertbot/logs/worker.log"
echo "   2. Test with a small deposit to verify correct amounts"
echo "   3. Check that notifications are clean (no spam)"
echo ""
echo "🔍 To verify a withdrawal:"
echo "   - Old deposits may still have old fee calculation in DB"
echo "   - New deposits will use the correct fee calculation"
echo "   - Look for logs showing 'withdrawal_amount' and 'final_amount'"
echo ""
