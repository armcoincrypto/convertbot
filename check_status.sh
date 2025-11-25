#!/bin/bash
# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

clear
echo "╔════════════════════════════════════════════════════════════╗"
echo "║           🔍 CONVERTBOT - SYSTEM STATUS                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

echo "⏰ Current Time: $(date)"
echo ""

echo "📊 Deposits by Status:"
sqlite3 swapbot.db "SELECT status, COUNT(*), GROUP_CONCAT(substr(txid,1,8)) FROM deposits GROUP BY status"
echo ""

echo "💰 Recent Activity (Last 5):"
sqlite3 swapbot.db "SELECT substr(inserted_at,12,8) as time, substr(txid,1,12), coin, status, confs || '/' || required_confs as conf FROM deposits ORDER BY inserted_at DESC LIMIT 5"
echo ""

echo "🔴 Any Errors:"
tail -20 logs/worker.log 2>/dev/null | grep "ERROR\|Exception\|Failed" | tail -5
echo ""

echo "✅ Last Success:"
tail -50 logs/worker.log 2>/dev/null | grep "✅.*complete\|WITHDRAWN" | tail -1
echo ""

echo "💵 MEXC Balances:"
source venv/bin/activate
python3 << 'PY'
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) or '.')
from libs.mexc_client import MEXCClient
from app.config import settings
mexc = MEXCClient(settings.mexc_api_key, settings.mexc_api_secret)
b = mexc.get_account_balance()
for coin in ['BTC', 'LTC', 'DASH', 'XMR', 'USDT']:
    if coin in b:
        total = float(b[coin].get('free', 0)) + float(b[coin].get('locked', 0))
        if total > 0:
            print(f"  {coin}: {total}")
PY
