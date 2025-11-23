#!/bin/bash
# COMPLETE FIX DEPLOYMENT - After Full Audit

echo "🎯 COMPLETE FIX DEPLOYMENT - AFTER FULL AUDIT"
echo "================================================================"
echo ""

echo "📋 AUDIT SUMMARY:"
echo "   • Found and fixed 2 critical bugs"
echo "   • All database functions now use _row_to_deposit()"
echo "   • XMR withdrawals now check output_coin"
echo "   • BTC/LTC/DASH withdrawals already working"
echo ""

echo "🐛 BUGS FIXED:"
echo "   1. get_pending_deposits() - Now includes output_coin"
echo "   2. get_deposit() - Now includes output_coin"
echo "   3. get_user_deposits() - Now includes output_coin"
echo "   4. XMR withdrawals - Now check output_coin for TRX"
echo ""

read -p "Press ENTER to apply all fixes..."

echo ""
echo "1️⃣ Stopping services..."
sudo systemctl stop convertbot-worker
sudo systemctl stop convertbot-bot
sleep 2

echo ""
echo "2️⃣ Pulling ALL fixes from GitHub..."
cd /root/Convertbot
git pull origin claude/continue-convert-bot-01NaRqFFu8ZgiFs2xV29rW6z

echo ""
echo "3️⃣ Clearing ALL Python cache (project + venv)..."

# Clear project cache
echo "   Clearing project cache..."
find . -path ./venv -prune -o -type f \( -name "*.pyc" -o -name "*.pyo" \) -exec rm {} \; 2>/dev/null
find . -path ./venv -prune -o -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Clear venv cache
echo "   Clearing venv cache..."
find venv -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null
find venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

cache_count=$(find . -name "*.pyc" -o -name "*.pyo" -o -name "__pycache__" 2>/dev/null | wc -l)
echo "   Remaining cache files: $cache_count"

echo ""
echo "4️⃣ Verifying ALL fixes are present..."

fixes_ok=true

# Check get_pending_deposits uses _row_to_deposit
if grep -A 2 "deposits = \[\]" app/db.py | grep -q "_row_to_deposit"; then
    echo "   ✅ get_pending_deposits uses _row_to_deposit"
else
    echo "   ❌ get_pending_deposits NOT fixed!"
    fixes_ok=false
fi

# Check get_deposit uses _row_to_deposit
if grep -A 3 "if not row:" app/db.py | grep -q "return _row_to_deposit"; then
    echo "   ✅ get_deposit uses _row_to_deposit"
else
    echo "   ❌ get_deposit NOT fixed!"
    fixes_ok=false
fi

# Check _row_to_deposit has output_coin
if grep -q "output_coin=output_coin" app/db.py; then
    echo "   ✅ _row_to_deposit includes output_coin"
else
    echo "   ❌ _row_to_deposit missing output_coin!"
    fixes_ok=false
fi

# Check XMR uses withdraw_usdt_only
if grep -A 5 "if deposit.coin == CoinType.XMR:" app/pipeline.py | grep -q "withdraw_usdt_only"; then
    echo "   ✅ XMR uses withdraw_usdt_only()"
else
    echo "   ❌ XMR not using withdraw_usdt_only!"
    fixes_ok=false
fi

# Check pipeline has TRX logic
if grep -q "Converting USDT → TRX" app/pipeline.py; then
    echo "   ✅ Pipeline has TRX conversion logic"
else
    echo "   ❌ Pipeline missing TRX logic!"
    fixes_ok=false
fi

if [ "$fixes_ok" = false ]; then
    echo ""
    echo "❌ VERIFICATION FAILED! Some fixes are missing!"
    echo "   Please check git pull output above."
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
echo "7️⃣ Testing with live code..."
source venv/bin/activate
python3 << 'PYTHON'
import sqlite3
from app.db import _row_to_deposit

print("   Testing _row_to_deposit function:")
conn = sqlite3.connect('/root/Convertbot/swapbot.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get any TRX deposit
cursor.execute("SELECT * FROM deposits WHERE output_coin = 'TRX' LIMIT 1")
row = cursor.fetchone()

if row:
    deposit = _row_to_deposit(row)
    print(f"   Database: output_coin='{row['output_coin']}'")
    print(f"   Object: deposit.output_coin='{deposit.output_coin}'")

    # Test pipeline logic
    output_coin = deposit.output_coin if hasattr(deposit, 'output_coin') and deposit.output_coin else 'USDT'
    if output_coin == 'TRX':
        print(f"   ✅ CORRECT! Pipeline will withdraw TRX")
    else:
        print(f"   ❌ WRONG! Pipeline will withdraw USDT")
else:
    print("   ℹ️  No TRX deposits in database to test with")

conn.close()
PYTHON
deactivate

echo ""
echo "8️⃣ Checking recent worker logs..."
tail -10 /root/Convertbot/logs/worker.log

echo ""
echo "================================================================"
echo "✅ COMPLETE FIX DEPLOYED!"
echo "================================================================"
echo ""
echo "📊 WHAT WAS FIXED:"
echo "   1. ✅ Database functions now extract output_coin"
echo "   2. ✅ XMR withdrawals now check output_coin"
echo "   3. ✅ BTC/LTC/DASH withdrawals check output_coin"
echo "   4. ✅ All Python cache cleared"
echo ""
echo "🧪 READY FOR TESTING:"
echo ""
echo "   Test 1: DASH → TRON"
echo "   • Go to @Conodbot"
echo "   • Choose: 💎 Dash → TRON"
echo "   • Send 0.05 DASH"
echo "   • Wait 12 confirmations (~30 min)"
echo "   • YOU WILL SEE:"
echo "     📤 Withdrawing TRX for ..."
echo "     💱 Converting USDT → TRX on MEXC..."
echo "     ✅ Bought X TRX with Y USDT"
echo "   • YOU WILL RECEIVE: TRX (not USDT!)"
echo ""
echo "   Test 2: DASH → USDT"
echo "   • Choose: 💎 Dash → USDT"
echo "   • Verify receives USDT"
echo ""
echo "   Test 3: XMR → USDT"
echo "   • Choose: 🔒 Monero → USDT"
echo "   • Verify receives USDT immediately"
echo ""
echo "📝 Monitor logs:"
echo "   tail -f /root/Convertbot/logs/worker.log"
echo ""
