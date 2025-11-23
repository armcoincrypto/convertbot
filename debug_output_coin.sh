#!/bin/bash
# Debug why output_coin is STILL not working

echo "🔍 DEEP DEBUGGING: WHY IS OUTPUT_COIN NOT WORKING?"
echo "=========================================="
echo ""

latest_txid="a33fc76d3cbbafcf"

echo "1️⃣ Check database for latest deposit:"
echo "---"
sqlite3 /root/Convertbot/swapbot.db << SQL
.mode line
SELECT
    substr(txid,1,16) as TXID,
    coin,
    output_coin,
    status,
    target_address
FROM deposits
WHERE txid LIKE '${latest_txid}%';
SQL

echo ""
echo "2️⃣ Check if output_coin column exists in database:"
echo "---"
sqlite3 /root/Convertbot/swapbot.db "PRAGMA table_info(deposits);" | grep output_coin

echo ""
echo "3️⃣ Check _row_to_deposit function in code:"
echo "---"
echo "Lines 22-44 of app/db.py:"
sed -n '22,44p' /root/Convertbot/app/db.py

echo ""
echo "4️⃣ Check pipeline withdraw_usdt_only function:"
echo "---"
echo "Lines 185-190 of app/pipeline.py:"
sed -n '185,190p' /root/Convertbot/app/pipeline.py

echo ""
echo "5️⃣ Test Python code directly:"
echo "---"
python3 << 'PYTHON'
import sqlite3
import sys
sys.path.insert(0, '/root/Convertbot')

# Connect to DB
conn = sqlite3.connect('/root/Convertbot/swapbot.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get latest deposit
cursor.execute("SELECT * FROM deposits WHERE txid LIKE 'a33fc76d3cbbafcf%'")
row = cursor.fetchone()

if row:
    print("Raw database row:")
    print(f"  txid: {row['txid'][:16]}...")
    print(f"  coin: {row['coin']}")
    print(f"  output_coin: {row['output_coin']}")
    print(f"  status: {row['status']}")
    print("")

    # Now test _row_to_deposit
    from app.db import _row_to_deposit
    deposit = _row_to_deposit(row)

    print("After _row_to_deposit conversion:")
    print(f"  deposit.coin: {deposit.coin}")
    print(f"  deposit.output_coin: {deposit.output_coin}")
    print(f"  deposit.status: {deposit.status}")
else:
    print("❌ Deposit not found!")

conn.close()
PYTHON

echo ""
echo "=========================================="
