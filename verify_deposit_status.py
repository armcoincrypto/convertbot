"""Verify the deposit status was changed"""
import asyncio
import aiosqlite
from app.config import settings

async def verify():
    db_path = settings.database_url.replace('sqlite:///', '')
    txid = "bf249c9802651f4a2a399f80ad82ec90bf3ad7527c9451c77584ce0fffee9777"

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT txid, coin, status, confs, required_confs FROM deposits WHERE txid = ?",
            (txid,)
        )
        row = await cursor.fetchone()

        if row:
            print("="*70)
            print("Current deposit status:")
            print(f"TXID: {row['txid'][:16]}...")
            print(f"Coin: {row['coin']}")
            print(f"Status: {row['status']}")
            print(f"Confirmations: {row['confs']}/{row['required_confs']}")
            print("="*70)
        else:
            print("❌ Deposit not found!")

if __name__ == "__main__":
    asyncio.run(verify())
