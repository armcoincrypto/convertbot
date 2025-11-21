#!/bin/bash
# Convertbot Monitoring Script
# Use this on your VPS to check system status

echo "🤖 CONVERTBOT SYSTEM STATUS"
echo "=========================================="
echo ""

# Check if services exist
if ! systemctl list-unit-files | grep -q convertbot-worker; then
    echo "❌ ERROR: Services not installed!"
    echo "   Run: cd /root/Convertbot && sudo bash setup_service.sh"
    exit 1
fi

echo "📡 Service Status:"
echo "---"
worker_status=$(systemctl is-active convertbot-worker)
bot_status=$(systemctl is-active convertbot-bot)

if [ "$worker_status" = "active" ]; then
    echo "✅ Worker: RUNNING"
else
    echo "❌ Worker: $worker_status"
fi

if [ "$bot_status" = "active" ]; then
    echo "✅ Bot: RUNNING"
else
    echo "❌ Bot: $bot_status"
fi

echo ""
echo "📊 Database Status:"
echo "---"
if [ -f /root/Convertbot/swapbot.db ]; then
    # Count deposits by status
    echo "Total deposits: $(sqlite3 /root/Convertbot/swapbot.db 'SELECT COUNT(*) FROM deposits')"
    echo "Pending/Confirming: $(sqlite3 /root/Convertbot/swapbot.db "SELECT COUNT(*) FROM deposits WHERE status IN ('NEW', 'CONFIRMING', 'CONFIRMED')")"
    echo "Sold (awaiting withdrawal): $(sqlite3 /root/Convertbot/swapbot.db "SELECT COUNT(*) FROM deposits WHERE status = 'SOLD'")"
    echo "Withdrawn (complete): $(sqlite3 /root/Convertbot/swapbot.db "SELECT COUNT(*) FROM deposits WHERE status = 'WITHDRAWN'")"
    echo "Failed: $(sqlite3 /root/Convertbot/swapbot.db "SELECT COUNT(*) FROM deposits WHERE status LIKE '%FAILED%'")"
else
    echo "❌ Database not found"
fi

echo ""
echo "📝 Recent Activity (last 5 deposits):"
echo "---"
sqlite3 /root/Convertbot/swapbot.db \
    "SELECT substr(txid,1,16) || '...', coin, output_coin, status, confs || '/' || required_confs
     FROM deposits
     ORDER BY inserted_at DESC
     LIMIT 5" \
    -header -column 2>/dev/null || echo "No deposits yet"

echo ""
echo "🔍 Worker Log (last 15 lines):"
echo "---"
if [ -f /root/Convertbot/logs/worker.log ]; then
    tail -15 /root/Convertbot/logs/worker.log
else
    echo "No worker log found"
fi

echo ""
echo "⚠️  Recent Errors (if any):"
echo "---"
if [ -f /root/Convertbot/logs/worker.log ]; then
    errors=$(grep "ERROR\|❌\|💥" /root/Convertbot/logs/worker.log | tail -5)
    if [ -n "$errors" ]; then
        echo "$errors"
    else
        echo "✅ No recent errors"
    fi
else
    echo "No error log found"
fi

echo ""
echo "=========================================="
echo "🛠️  Quick Commands:"
echo "   Restart worker:  sudo systemctl restart convertbot-worker"
echo "   Restart bot:     sudo systemctl restart convertbot-bot"
echo "   View worker log: tail -f /root/Convertbot/logs/worker.log"
echo "   View bot log:    tail -f /root/Convertbot/logs/bot.log"
echo ""
