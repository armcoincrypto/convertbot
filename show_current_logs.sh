#!/bin/bash
# Show current Convertbot logs

echo "📊 CONVERTBOT CURRENT STATUS"
echo "=========================================="
echo ""

echo "1️⃣ Service Status:"
echo "---"
worker_status=$(systemctl is-active convertbot-worker 2>/dev/null || echo "not running")
bot_status=$(systemctl is-active convertbot-bot 2>/dev/null || echo "not running")
echo "Worker: $worker_status"
echo "Bot: $bot_status"

echo ""
echo "2️⃣ Worker Log (last 50 lines):"
echo "---"
if [ -f /root/Convertbot/logs/worker.log ]; then
    tail -50 /root/Convertbot/logs/worker.log
else
    echo "No worker log found"
fi

echo ""
echo "=========================================="
echo ""
echo "3️⃣ Looking for withdrawal-related activity:"
echo "---"
if [ -f /root/Convertbot/logs/worker.log ]; then
    echo "Last 10 withdrawal messages:"
    grep -i "withdrawing\|withdrawal\|converting usdt" /root/Convertbot/logs/worker.log | tail -10
else
    echo "No logs found"
fi

echo ""
echo "4️⃣ Database - Recent deposits:"
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
    datetime(inserted_at, 'localtime') as Time
FROM deposits
ORDER BY inserted_at DESC
LIMIT 5;
SQL
else
    echo "Database not found"
fi

echo ""
echo "=========================================="
