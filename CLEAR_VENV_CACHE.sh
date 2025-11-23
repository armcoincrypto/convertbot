#!/bin/bash
# Clear Python cache in VENV (this was the missing step!)

echo "🔥 CLEARING VENV PYTHON CACHE"
echo "=========================================="
echo ""

echo "🐛 THE REAL PROBLEM:"
echo "   We cleared cache in /root/Convertbot but NOT in /root/Convertbot/venv!"
echo "   The venv has 557 cached .pyc files with OLD bytecode!"
echo ""

echo "1️⃣ Stopping services..."
sudo systemctl stop convertbot-worker
sudo systemctl stop convertbot-bot
sleep 2

echo ""
echo "2️⃣ Checking venv cache before cleanup..."
cache_before=$(find /root/Convertbot/venv -name "*.pyc" -o -name "__pycache__" 2>/dev/null | wc -l)
echo "   Cache files in venv: $cache_before"

echo ""
echo "3️⃣ Clearing venv cache..."
cd /root/Convertbot

# Clear venv cache
find venv -type f -name "*.pyc" -delete 2>/dev/null
find venv -type f -name "*.pyo" -delete 2>/dev/null
find venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Also clear project cache again
find . -path ./venv -prune -o -type f -name "*.pyc" -exec rm {} \; 2>/dev/null
find . -path ./venv -prune -o -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

echo ""
echo "4️⃣ Checking cache after cleanup..."
cache_after=$(find /root/Convertbot/venv -name "*.pyc" -o -name "__pycache__" 2>/dev/null | wc -l)
echo "   Cache files in venv: $cache_after"
echo "   Deleted: $(($cache_before - $cache_after)) files"

echo ""
echo "5️⃣ Verifying code is correct..."
echo "   Checking _row_to_deposit has output_coin:"
if grep -q "output_coin=output_coin" app/db.py; then
    echo "   ✅ app/db.py has fix"
else
    echo "   ❌ app/db.py missing fix!"
fi

echo "   Checking pipeline checks output_coin:"
if grep -q "Withdrawing {output_coin}" app/pipeline.py; then
    echo "   ✅ app/pipeline.py has fix"
else
    echo "   ❌ app/pipeline.py missing fix!"
fi

echo ""
echo "6️⃣ Starting services with FRESH bytecode..."
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
echo "8️⃣ Testing the fix with live code..."
source venv/bin/activate
python3 << 'PYTHON'
import sqlite3
from app.db import _row_to_deposit

conn = sqlite3.connect('/root/Convertbot/swapbot.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT * FROM deposits WHERE txid LIKE 'a33fc76d3cbbafcf%'")
row = cursor.fetchone()

if row:
    deposit = _row_to_deposit(row)
    output_coin = deposit.output_coin if hasattr(deposit, 'output_coin') and deposit.output_coin else 'USDT'
    print(f"   Database output_coin: '{row['output_coin']}'")
    print(f"   Deposit object output_coin: '{deposit.output_coin}'")
    print(f"   Pipeline will use: '{output_coin}'")

    if output_coin == 'TRX':
        print("   ✅ TRX withdrawal will be triggered!")
    else:
        print("   ❌ USDT withdrawal will be triggered (BUG!)")

conn.close()
PYTHON
deactivate

echo ""
echo "9️⃣ Checking worker logs..."
tail -5 /root/Convertbot/logs/worker.log

echo ""
echo "=========================================="
echo "✅ VENV CACHE CLEARED!"
echo ""
echo "🧪 CRITICAL TEST:"
echo "   Create a NEW DASH → TRON deposit in @Conodbot"
echo "   This time you MUST see:"
echo "   📤 Withdrawing TRX for ..."
echo "   💱 Converting USDT → TRX on MEXC..."
echo "   And receive TRX (not USDT)!"
echo ""
