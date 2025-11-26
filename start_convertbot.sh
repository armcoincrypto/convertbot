#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate

echo "🚀 Starting Convertbot services..."

# Kill any existing processes
pkill -f "telegram_bot_improved.py"
pkill -f "app.worker"
sleep 2

# Start bot
nohup python telegram_bot_improved.py > bot.log 2>&1 &
BOT_PID=$!
echo "✅ Bot started (PID: $BOT_PID)"

# Start worker
nohup python -m app.worker > worker.log 2>&1 &
WORKER_PID=$!
echo "✅ Worker started (PID: $WORKER_PID)"

sleep 2
echo ""
echo "📊 Services running:"
ps aux | grep -E "app.worker|telegram_bot" | grep -v grep | head -2

echo ""
echo "✅ Convertbot started! Monitor with: ./live_logs.sh"
