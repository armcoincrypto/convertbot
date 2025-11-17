#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

clear
echo "╔═══════════════════════════════════════════════════════╗"
echo "║     🔴 CONVERTBOT LIVE LOGS                          ║"
echo "╚═══════════════════════════════════════════════════════╝"

# Check if services are running
WORKER_PID=$(ps aux | grep "app.worker" | grep -v grep | awk '{print $2}')
BOT_PID=$(ps aux | grep "telegram_bot_improved.py" | grep -v grep | awk '{print $2}')

echo ""
echo "📊 Status:"
if [ -n "$WORKER_PID" ]; then
    echo -e "  ${GREEN}✅ Worker running (PID: $WORKER_PID)${NC}"
else
    echo -e "  ${RED}❌ Worker NOT running${NC}"
fi

if [ -n "$BOT_PID" ]; then
    echo -e "  ${GREEN}✅ Bot running (PID: $BOT_PID)${NC}"
else
    echo -e "  ${RED}❌ Bot NOT running${NC}"
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "📜 Last 30 lines, then live updates..."
echo "═══════════════════════════════════════════════════════"
echo ""

# Function to colorize output
colorize() {
    while IFS= read -r line; do
        if [[ $line == *"ERROR"* ]] || [[ $line == *"FATAL"* ]] || [[ $line == *"❌"* ]]; then
            echo -e "${RED}$line${NC}"
        elif [[ $line == *"WARNING"* ]] || [[ $line == *"⚠️"* ]]; then
            echo -e "${YELLOW}$line${NC}"
        elif [[ $line == *"SUCCESS"* ]] || [[ $line == *"✅"* ]] || [[ $line == *"COMPLETE"* ]] || [[ $line == *"Pipeline completed"* ]]; then
            echo -e "${GREEN}$line${NC}"
        elif [[ $line == *"Trade"* ]] || [[ $line == *"Withdrawal"* ]] || [[ $line == *"Selling"* ]]; then
            echo -e "${CYAN}$line${NC}"
        elif [[ $line == *"CONFIRMED"* ]] || [[ $line == *"🎉"* ]]; then
            echo -e "${MAGENTA}$line${NC}"
        elif [[ $line == *"==> worker.log <==" ]]; then
            echo -e "${BLUE}$line${NC}"
        elif [[ $line == *"==> bot.log <==" ]]; then
            echo -e "${BLUE}$line${NC}"
        else
            echo "$line"
        fi
    done
}

# Show last 30 lines from both logs
(tail -30 worker.log 2>/dev/null; tail -30 bot.log 2>/dev/null) | tail -30 | colorize

echo ""
echo "━━━━━━━━━━━━━━ LIVE UPDATES BELOW ━━━━━━━━━━━━━━"
echo ""

# Now follow both logs
tail -f worker.log bot.log 2>/dev/null | colorize
