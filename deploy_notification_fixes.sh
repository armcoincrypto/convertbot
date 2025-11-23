#!/bin/bash
# Deploy notification removal fixes

echo "🔕 NOTIFICATION FIXES DEPLOYMENT"
echo "================================================================"
echo ""

echo "📋 CHANGES TO DEPLOY:"
echo "   • Remove 'Deposit confirmed!' at early confirmations"
echo "   • Remove TRADE_FAILED error notifications (auto-retry will fix)"
echo ""

read -p "Press ENTER to deploy notification fixes..."

echo ""
echo "1️⃣ Stopping services..."
sudo systemctl stop convertbot-worker convertbot-bot
sleep 2

echo ""
echo "2️⃣ Pulling notification fixes from GitHub..."
cd /root/Convertbot
git pull origin claude/continue-convert-bot-01NaRqFFu8ZgiFs2xV29rW6z

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

# Check worker.py - should NOT have the notification
if grep -A 5 "elif confs >= deposit.required_confs:" app/worker.py | grep -q "send_message"; then
    echo "   ❌ worker.py still has 'Deposit confirmed!' notification!"
    fixes_ok=false
else
    echo "   ✅ worker.py - 'Deposit confirmed!' notification removed"
fi

# Check pipeline.py - should NOT notify on TRADE_FAILED
if grep -A 3 "Trade failed:" app/pipeline.py | grep -q "_notify_error"; then
    echo "   ❌ pipeline.py still notifies on TRADE_FAILED!"
    fixes_ok=false
else
    echo "   ✅ pipeline.py - TRADE_FAILED error notification removed"
fi

if [ "$fixes_ok" = false ]; then
    echo ""
    echo "❌ VERIFICATION FAILED!"
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
echo "✅ NOTIFICATION FIXES DEPLOYED!"
echo "================================================================"
echo ""
echo "📊 WHAT CHANGED:"
echo "   1. ✅ No more 'Deposit confirmed!' at 2 confirmations"
echo "   2. ✅ No more TRADE_FAILED error notifications"
echo ""
echo "🎯 USER EXPERIENCE IMPROVEMENTS:"
echo "   • Users only get notified when they receive funds"
echo "   • No confusing error messages for auto-retried trades"
echo "   • Cleaner notification flow"
echo ""
echo "📝 Monitor logs:"
echo "   tail -f /root/Convertbot/logs/worker.log"
echo ""
