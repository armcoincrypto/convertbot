"""Test script to verify the row.get() fix in database queries."""
import asyncio
from app.db import get_pending_deposits, init_db

async def test():
    print("🔧 Testing database fix...")
    print("-" * 50)

    try:
        await init_db()
        print("✅ Database initialized")

        deposits = await get_pending_deposits()
        print(f"✅ Successfully fetched {len(deposits)} deposits")
        print("-" * 50)

        if deposits:
            print("\nDeposit details:")
            for i, d in enumerate(deposits[:5], 1):
                print(f"\n{i}. TXID: {d.txid[:16]}...")
                print(f"   Status: {d.status.value}")
                print(f"   Coin: {d.coin.value}")
                print(f"   USDT Amount: {d.usdt_amount}")
                print(f"   Final USDT: {d.final_usdt}")
                print(f"   Confirmations: {d.confs}/{d.required_confs}")
        else:
            print("\nNo pending deposits found.")

        print("\n" + "=" * 50)
        print("✅ TEST PASSED: No row.get() errors!")
        print("=" * 50)

    except AttributeError as e:
        if "has no attribute 'get'" in str(e):
            print("\n❌ TEST FAILED: row.get() error still exists!")
            print(f"Error: {e}")
        else:
            raise
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
