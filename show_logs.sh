#!/bin/bash
# Show recent Convertbot logs

echo "📝 CONVERTBOT RECENT LOGS"
echo "=========================================="
echo ""

echo "1️⃣ Worker Log (last 50 lines):"
echo "---"
if [ -f /root/Convertbot/logs/worker.log ]; then
    tail -50 /root/Convertbot/logs/worker.log
else
    echo "❌ Worker log not found"
fi

echo ""
echo "=========================================="
echo ""
echo "2️⃣ Bot Log (last 30 lines):"
echo "---"
if [ -f /root/Convertbot/logs/bot.log ]; then
    tail -30 /root/Convertbot/logs/bot.log
else
    echo "❌ Bot log not found"
fi

echo ""
echo "=========================================="
echo ""
echo "3️⃣ Recent Withdrawals in Logs:"
echo "---"
if [ -f /root/Convertbot/logs/worker.log ]; then
    echo "Last 10 withdrawal-related messages:"
    grep -i "withdrawing\|withdrawal\|converting usdt" /root/Convertbot/logs/worker.log | tail -10
else
    echo "❌ No logs found"
fi

echo ""
echo "=========================================="
echo ""
echo "4️⃣ Database Status:"
echo "---"
if [ -f /root/Convertbot/swapbot.db ]; then
    sqlite3 /root/Convertbot/swapbot.db << 'SQL'
.mode column
.headers on
SELECT
    substr(txid,1,16) || '...' as TXID,
    coin,
    output_coin,
    status,
    confs || '/' || required_confs as Confs,
    datetime(inserted_at) as Inserted
FROM deposits
ORDER BY inserted_at DESC
LIMIT 5;
SQL
else
    echo "❌ Database not found"
fi

echo ""
echo "=========================================="
