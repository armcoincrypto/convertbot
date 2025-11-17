"""Fix existing TRADE_FAILED deposits that should be AMOUNT_TOO_SMALL"""
import asyncio
import aiosqlite
from app.config import settings

async def fix_deposits():
    """Change existing TRADE_FAILED deposits to AMOUNT_TOO_SMALL"""
    db_path = settings.database_url.replace('sqlite:///', '')

    async with aiosqlite.connect(db_path) as db:
        # Get all TRADE_FAILED deposits
        cursor = await db.execute(
            "SELECT txid FROM deposits WHERE status = 'TRADE_FAILED'"
        )
        failed_deposits = await cursor.fetchall()

        if not failed_deposits:
            print("✅ No TRADE_FAILED deposits found")
            return

        print(f"🔧 Found {len(failed_deposits)} TRADE_FAILED deposits")
        print(f"🔄 Changing them to AMOUNT_TOO_SMALL status...\n")

        # Update them to AMOUNT_TOO_SMALL
        await db.execute(
            "UPDATE deposits SET status = 'AMOUNT_TOO_SMALL' WHERE status = 'TRADE_FAILED'"
        )
        await db.commit()

        print(f"✅ Updated {len(failed_deposits)} deposits to AMOUNT_TOO_SMALL")
        print(f"✅ These deposits will no longer be auto-retried")
        print(f"\nDeposits updated:")
        for row in failed_deposits:
            print(f"  - {row[0][:16]}...")

if __name__ == "__main__":
    print("="*60)
    print("Fix TRADE_FAILED deposits")
    print("="*60)
    asyncio.run(fix_deposits())
    print("="*60)
