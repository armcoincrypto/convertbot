#!/bin/bash
# Verify that VPS has the correct TRX withdrawal code

echo "🔍 VERIFYING VPS CODE FOR TRX WITHDRAWALS"
echo "=========================================="
echo ""

echo "1️⃣ Checking if pipeline.py has TRX conversion logic:"
echo "---"
if grep -q "Converting USDT → TRX" /root/Convertbot/app/pipeline.py; then
    echo "✅ Found: 'Converting USDT → TRX' message"
else
    echo "❌ MISSING: TRX conversion logic not found!"
fi

if grep -q "output_coin = deposit.output_coin" /root/Convertbot/app/pipeline.py; then
    echo "✅ Found: output_coin detection"
else
    echo "❌ MISSING: output_coin detection not found!"
fi

if grep -q "buy_crypto_with_usdt('TRX'" /root/Convertbot/app/pipeline.py; then
    echo "✅ Found: TRX purchase logic"
else
    echo "❌ MISSING: TRX purchase logic not found!"
fi

if grep -q "withdraw_trx" /root/Convertbot/app/pipeline.py; then
    echo "✅ Found: TRX withdrawal call"
else
    echo "❌ MISSING: TRX withdrawal call not found!"
fi

echo ""
echo "2️⃣ Checking mexc_client.py has TRX functions:"
echo "---"
if grep -q "def withdraw_trx" /root/Convertbot/libs/mexc_client.py; then
    echo "✅ Found: withdraw_trx function"
else
    echo "❌ MISSING: withdraw_trx function not found!"
fi

if grep -q "def buy_crypto_with_usdt" /root/Convertbot/libs/mexc_client.py; then
    echo "✅ Found: buy_crypto_with_usdt function"
else
    echo "❌ MISSING: buy_crypto_with_usdt function not found!"
fi

echo ""
echo "3️⃣ Checking Git branch and commit:"
echo "---"
cd /root/Convertbot
echo "Current branch: $(git branch --show-current)"
echo "Latest commit: $(git log -1 --oneline)"

echo ""
echo "4️⃣ Checking database deposits:"
echo "---"
sqlite3 /root/Convertbot/swapbot.db << 'SQL'
.mode column
.headers on
SELECT
    substr(txid,1,16) || '...' as TXID,
    coin,
    output_coin,
    status,
    CAST(usdt_amount AS TEXT) as USDT,
    CAST(final_usdt AS TEXT) as Final
FROM deposits
ORDER BY inserted_at DESC
LIMIT 5;
SQL

echo ""
echo "5️⃣ Checking Python cache cleared:"
echo "---"
pycache_count=$(find /root/Convertbot -name "*.pyc" -o -name "__pycache__" 2>/dev/null | wc -l)
if [ "$pycache_count" -eq 0 ]; then
    echo "✅ No Python cache files found (good!)"
else
    echo "⚠️  Found $pycache_count cache files/dirs (should clear again)"
fi

echo ""
echo "=========================================="
echo "✅ VERIFICATION COMPLETE"
echo ""
