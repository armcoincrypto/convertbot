#!/bin/bash
echo "
╔════════════════════════════════════════════════════════════╗
║              📊 CONVERTBOT - LIVE MONITORING               ║
╚════════════════════════════════════════════════════════════╝
"

# Color output
tail -f worker.log | while read line; do
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
