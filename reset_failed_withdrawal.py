"""Reset failed withdrawal back to SOLD status"""
import asyncio
import aiosqlite
from app.config import settings

async def reset_withdrawal():
    db_path = settings.database_url.replace('sqlite:///', '')

    # The DASH deposit that failed
    txid = "bf249c9802651f4a2a399f80ad82ec90bf3ad7527c9451c77584ce0fffee9777"

    async with aiosqlite.connect(db_path) as db:
        # Update status back to SOLD
        await db.execute(
            "UPDATE deposits SET status = 'SOLD' WHERE txid = ?",
            (txid,)
        )
        await db.commit()

        print("="*70)
        print("✅ Reset deposit status from WITHDRAWN → SOLD")
        print(f"TXID: {txid[:16]}...")
        print("\nThe worker will now retry the withdrawal with the new API key!")
        print("="*70)

if __name__ == "__main__":
    asyncio.run(reset_withdrawal())
