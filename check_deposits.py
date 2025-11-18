"""Check deposit status in database"""
import asyncio
import aiosqlite
from app.config import settings

async def check_deposits():
    db_path = settings.database_url.replace('sqlite:///', '')

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row

        # Get all deposits
        cursor = await db.execute("""
            SELECT txid, coin, status, confs, required_confs,
                   usdt_amount, final_usdt, inserted_at
            FROM deposits
            ORDER BY inserted_at DESC
            LIMIT 10
        """)
        rows = await cursor.fetchall()

        if not rows:
            print("❌ No deposits found in database")
            return

        print("="*70)
        print("Recent Deposits:")
        print("="*70)

        for row in rows:
            txid_short = row['txid'][:16] if row['txid'] else 'N/A'
            print(f"\n📋 TXID: {txid_short}...")
            print(f"   Coin: {row['coin']}")
            print(f"   Status: {row['status']}")
            print(f"   Confirmations: {row['confs']}/{row['required_confs']}")
            print(f"   USDT: {row['usdt_amount']} → Final: {row['final_usdt']}")
            print(f"   Date: {row['inserted_at']}")

        print("\n" + "="*70)

        # Check for SOLD deposits specifically
        cursor = await db.execute("""
            SELECT COUNT(*) as count FROM deposits WHERE status = 'SOLD'
        """)
        sold_count = (await cursor.fetchone())[0]
        print(f"Deposits in SOLD status: {sold_count}")

        # Check for WITHDRAWN deposits
        cursor = await db.execute("""
            SELECT COUNT(*) as count FROM deposits WHERE status = 'WITHDRAWN'
        """)
        withdrawn_count = (await cursor.fetchone())[0]
        print(f"Deposits in WITHDRAWN status: {withdrawn_count}")
        print("="*70)

if __name__ == "__main__":
    asyncio.run(check_deposits())
