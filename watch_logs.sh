#!/bin/bash
# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "
╔════════════════════════════════════════════════════════════╗
║              📊 CONVERTBOT - LIVE MONITORING               ║
╚════════════════════════════════════════════════════════════╝
"

# Check for log files in multiple locations
LOG_FILE=""
if [ -f "/var/log/convertbot/worker.log" ]; then
    LOG_FILE="/var/log/convertbot/worker.log"
elif [ -f "logs/worker.log" ]; then
    LOG_FILE="logs/worker.log"
elif [ -f "worker.log" ]; then
    LOG_FILE="worker.log"
else
    echo "No log file found. Starting to watch journalctl..."
    journalctl -u convertbot-worker -f
    exit 0
fi

echo "Watching: $LOG_FILE"
echo ""

# Color output
tail -f "$LOG_FILE" | while read line; do
    if echo "$line" | grep -q "ERROR\|❌\|FAILED"; then
        echo -e "\033[0;31m$line\033[0m"  # Red
    elif echo "$line" | grep -q "✅\|SUCCESS\|WITHDRAWN"; then
        echo -e "\033[0;32m$line\033[0m"  # Green
    elif echo "$line" | grep -q "⚠️\|WARNING"; then
        echo -e "\033[0;33m$line\033[0m"  # Yellow
    elif echo "$line" | grep -q "🔄\|Processing\|CONFIRMED\|SOLD"; then
        echo -e "\033[0;36m$line\033[0m"  # Cyan
    else
        echo "$line"
    fi
done
