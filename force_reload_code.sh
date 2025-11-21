#!/bin/bash
# Force Python to reload the new code by clearing ALL cache

echo "🔄 FORCE RELOADING CONVERTBOT CODE"
echo "=========================================="
echo ""

echo "1️⃣ Stopping services..."
sudo systemctl stop convertbot-worker
sudo systemctl stop convertbot-bot
sleep 2

echo ""
echo "2️⃣ Clearing ALL Python cache files..."
cd /root/Convertbot

# Method 1: Remove __pycache__ directories
echo "   Removing __pycache__ directories..."
find . -type d -name "__pycache__" -print -exec rm -rf {} + 2>/dev/null || true

# Method 2: Remove .pyc files
echo "   Removing .pyc files..."
find . -type f -name "*.pyc" -print -delete 2>/dev/null || true

# Method 3: Remove .pyo files
echo "   Removing .pyo files..."
find . -type f -name "*.pyo" -print -delete 2>/dev/null || true

# Verify cleanup
cache_count=$(find . -name "*.pyc" -o -name "*.pyo" -o -name "__pycache__" 2>/dev/null | wc -l)
echo "   Remaining cache files: $cache_count"

echo ""
echo "3️⃣ Verifying code is latest..."
echo "   Current commit: $(git log -1 --oneline)"
echo "   Checking TRX logic..."
if grep -q "Converting USDT → TRX" app/pipeline.py; then
    echo "   ✅ TRX conversion code present"
else
    echo "   ❌ ERROR: TRX code missing!"
    exit 1
fi

echo ""
echo "4️⃣ Starting services with fresh code..."
sudo systemctl start convertbot-worker
sleep 3
sudo systemctl start convertbot-bot
sleep 2

echo ""
echo "5️⃣ Checking service status..."
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
echo "6️⃣ Checking recent worker logs..."
echo "   Last 10 lines:"
tail -10 /root/Convertbot/logs/worker.log

echo ""
echo "=========================================="
echo "✅ CODE RELOAD COMPLETE"
echo ""
echo "🎯 Next: Test with new DASH → TRON deposit"
echo "   The next deposit should withdraw TRX (not USDT)!"
echo ""
