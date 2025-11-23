#!/bin/bash
# Test the ACTUAL running code with venv

echo "🔍 TESTING LIVE CODE WITH VENV"
echo "=========================================="
echo ""

cd /root/Convertbot

echo "1️⃣ Activating venv and testing _row_to_deposit:"
echo "---"
source venv/bin/activate

python3 << 'PYTHON'
import sqlite3
import sys

# Connect to DB
conn = sqlite3.connect('/root/Convertbot/swapbot.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get latest deposit
cursor.execute("SELECT * FROM deposits WHERE txid LIKE 'a33fc76d3cbbafcf%'")
row = cursor.fetchone()

if row:
    print("✅ Raw database row:")
    print(f"   txid: {row['txid'][:16]}...")
    print(f"   coin: {row['coin']}")
    print(f"   output_coin: '{row['output_coin']}'")
    print(f"   status: {row['status']}")
    print("")

    # Now test _row_to_deposit
    from app.db import _row_to_deposit
    deposit = _row_to_deposit(row)

    print("✅ After _row_to_deposit conversion:")
    print(f"   deposit.coin: {deposit.coin}")
    print(f"   deposit.output_coin: '{deposit.output_coin}'")
    print(f"   deposit.status: {deposit.status}")
    print(f"   hasattr(deposit, 'output_coin'): {hasattr(deposit, 'output_coin')}")
    print("")

    # Test the condition from pipeline.py line 186
    output_coin = deposit.output_coin if hasattr(deposit, 'output_coin') and deposit.output_coin else 'USDT'
    print("🎯 What pipeline.py sees:")
    print(f"   hasattr(deposit, 'output_coin'): {hasattr(deposit, 'output_coin')}")
    print(f"   deposit.output_coin: '{deposit.output_coin}'")
    print(f"   deposit.output_coin evaluates to: {bool(deposit.output_coin)}")
    print(f"   Final output_coin value: '{output_coin}'")

else:
    print("❌ Deposit not found!")

conn.close()
PYTHON

deactivate

echo ""
echo "=========================================="
