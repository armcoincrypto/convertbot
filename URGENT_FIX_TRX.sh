#!/bin/bash
# URGENT: Apply critical fix for TRX withdrawals

echo "🚨 APPLYING CRITICAL TRX WITHDRAWAL FIX"
echo "=========================================="
echo ""

echo "🐛 THE BUG:"
echo "   The _row_to_deposit function in app/db.py was missing the"
echo "   output_coin field, causing ALL deposits to default to USDT"
echo "   even when output_coin='TRX' was in the database."
echo ""

echo "✅ THE FIX:"
echo "   Added output_coin extraction from database rows"
echo ""

echo "1️⃣ Stopping services..."
sudo systemctl stop convertbot-worker
sudo systemctl stop convertbot-bot
sleep 2

echo ""
echo "2️⃣ Pulling latest fix from GitHub..."
cd /root/Convertbot
git pull origin claude/continue-convert-bot-01NaRqFFu8ZgiFs2xV29rW6z

echo ""
echo "3️⃣ Clearing Python cache (CRITICAL!)..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null

cache_count=$(find . -name "*.pyc" -o -name "*.pyo" -o -name "__pycache__" 2>/dev/null | wc -l)
echo "   Remaining cache files: $cache_count"

echo ""
echo "4️⃣ Verifying fix is present..."
if grep -q "output_coin=output_coin" app/db.py; then
    echo "   ✅ Fix confirmed in app/db.py"
else
    echo "   ❌ ERROR: Fix not found! Check git pull output above."
    exit 1
fi

echo ""
echo "5️⃣ Starting services with fixed code..."
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
echo "7️⃣ Checking worker logs..."
tail -10 /root/Convertbot/logs/worker.log

echo ""
echo "=========================================="
echo "✅ CRITICAL FIX APPLIED!"
echo ""
echo "🎯 What changed:"
echo "   - app/db.py: _row_to_deposit now extracts output_coin from database"
echo "   - Deposits with output_coin='TRX' will now properly trigger TRX withdrawals"
echo "   - All Python cache cleared to force reload"
echo ""
echo "🧪 Test now:"
echo "   1. Create new DASH → TRON swap in @Conodbot"
echo "   2. Send 0.05 DASH"
echo "   3. Watch: tail -f /root/Convertbot/logs/worker.log"
echo "   4. After 12 confirmations, you should see:"
echo "      💱 Converting USDT → TRX on MEXC..."
echo "      ✅ Bought X TRX with Y USDT"
echo "   5. You'll receive TRX (not USDT)!"
echo ""
