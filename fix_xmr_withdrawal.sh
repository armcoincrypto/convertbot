#!/bin/bash
# Fix XMR withdrawal bug and retry failed withdrawal

echo "🔧 XMR WITHDRAWAL FIX"
echo "================================================================"
echo ""
echo "📋 WHAT THIS SCRIPT DOES:"
echo "   1. Deploy the XMR withdrawal bug fix"
echo "   2. Retry the failed XMR withdrawal (185457b60ed796d1...)"
echo ""
echo "🐛 BUG FIXED:"
echo "   - XMR withdrawals were failing with 'No stored USDT amount'"
echo "   - Deposit object wasn't reloaded after database update"
echo "   - Now reloads deposit before withdrawal"
echo ""

read -p "Press ENTER to deploy fix and retry withdrawal..."

echo ""
echo "1️⃣ Stopping services..."
sudo systemctl stop convertbot-worker convertbot-bot
sleep 2

echo ""
echo "2️⃣ Pulling XMR withdrawal fix from GitHub..."
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
echo "4️⃣ Verifying fix is present..."
if grep -q "Reload deposit from DB to get updated USDT amounts" app/pipeline.py; then
    echo "   ✅ XMR withdrawal fix present"
else
    echo "   ❌ XMR withdrawal fix NOT found!"
    exit 1
fi

echo ""
echo "5️⃣ Retrying failed XMR withdrawal..."
echo "   Changing status from WITHDRAWAL_FAILED → SOLD"

sqlite3 /root/Convertbot/swapbot.db << 'SQL'
UPDATE deposits
SET status = 'SOLD'
WHERE txid = '185457b60ed796d14f1e0b43c707440fee064c2a92c92dbe97b0705f7ba36583'
  AND status = 'WITHDRAWAL_FAILED';

SELECT 'Updated deposit status to: ' || status
FROM deposits
WHERE txid = '185457b60ed796d14f1e0b43c707440fee064c2a92c92dbe97b0705f7ba36583';
SQL

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
echo "✅ XMR FIX DEPLOYED AND WITHDRAWAL RETRYING!"
echo "================================================================"
echo ""
echo "📊 WHAT HAPPENS NEXT:"
echo "   • Worker will pick up the SOLD deposit"
echo "   • Reload deposit with updated USDT amounts"
echo "   • Withdraw 23.27 USDT to user's address"
echo "   • MEXC deducts 1 USDT fee"
echo "   • User receives 22.27 USDT"
echo "   • Telegram notification sent"
echo ""
echo "📝 Monitor the withdrawal:"
echo "   tail -f /root/Convertbot/logs/worker.log"
echo ""
echo "🔍 Look for these log messages:"
echo "   • '✅ Reloaded deposit with USDT amounts: 23.99 / 23.27'"
echo "   • '💵 Withdrawing 23.27 USDT (user receives 22.27 after MEXC 1.00 fee)'"
echo "   • '✅ Withdrawal successful'"
echo ""
