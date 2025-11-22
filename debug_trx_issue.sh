#!/bin/bash
# Debug why TRX withdrawal isn't working

echo "🔍 DEBUGGING TRX WITHDRAWAL ISSUE"
echo "=========================================="
echo ""

withdrawal_id="a4503c721a9e46f395f43f9ef2c710ae"

echo "1️⃣ Finding deposit by withdrawal message..."
echo "   Looking for TXID that just withdrew USDT..."
sqlite3 /root/Convertbot/swapbot.db << 'SQL'
.mode line
SELECT
    txid,
    coin,
    output_coin,
    status,
    usdt_amount,
    final_usdt,
    target_address,
    inserted_at
FROM deposits
WHERE status = 'WITHDRAWN'
ORDER BY inserted_at DESC
LIMIT 1;
SQL

echo ""
echo "2️⃣ Checking worker logs for withdrawal process..."
echo "   Last 50 lines containing 'Withdrawing' or 'output_coin'..."
grep -i "withdrawing\|output_coin\|Converting USDT" /root/Convertbot/logs/worker.log | tail -50

echo ""
echo "3️⃣ Checking if withdraw_usdt_only function is being called..."
echo "   Looking for withdrawal messages in logs..."
grep "📤 Withdrawing" /root/Convertbot/logs/worker.log | tail -10

echo ""
echo "4️⃣ Checking actual code in pipeline.py..."
echo "   First 30 lines of withdraw_usdt_only function:"
sed -n '/^async def withdraw_usdt_only/,/^async def\|^def/p' /root/Convertbot/app/pipeline.py | head -30

echo ""
echo "=========================================="
