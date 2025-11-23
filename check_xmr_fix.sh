#!/bin/bash
# Direct file check

echo "Checking what's actually in app/pipeline.py..."
echo ""

echo "Lines 114-125 (XMR section):"
sed -n '114,125p' /root/Convertbot/app/pipeline.py

echo ""
echo "Searching for withdraw_usdt_only in XMR section:"
sed -n '114,130p' /root/Convertbot/app/pipeline.py | grep -n "withdraw_usdt_only"

echo ""
echo "If you see 'success = await withdraw_usdt_only(deposit)' above, the fix IS there!"
