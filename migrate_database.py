#!/usr/bin/env python3
"""
Database Migration Script
Adds security and tracking features to Convertbot database
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = "swapbot.db"

def run_migration():
    """Run database migrations"""
    print("🔄 Running database migrations...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Migration 1: Add blacklist table
        print("\n1️⃣ Creating blacklist table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blacklist (
                txid TEXT PRIMARY KEY,
                reason TEXT NOT NULL,
                added_by INTEGER NOT NULL,
                added_at TEXT NOT NULL
            )
        """)
        print("   ✅ Blacklist table created")

        # Migration 2: Add attempt_count column to deposits
        print("\n2️⃣ Adding attempt_count to deposits table...")
        try:
            cursor.execute("ALTER TABLE deposits ADD COLUMN attempt_count INTEGER DEFAULT 0")
            print("   ✅ attempt_count column added")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("   ⚠️  attempt_count column already exists")
            else:
                raise

        # Migration 3: Add indexes for performance
        print("\n3️⃣ Creating performance indexes...")

        # Index on user_id + inserted_at for quota checks
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_deposits_user_date
            ON deposits(user_id, inserted_at)
        """)
        print("   ✅ Index on user_id+inserted_at created")

        # Index on status for worker queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_deposits_status
            ON deposits(status)
        """)
        print("   ✅ Index on status created")

        # Commit all changes
        conn.commit()

        print("\n" + "="*60)
        print("✅ ALL MIGRATIONS COMPLETED SUCCESSFULLY")
        print("="*60)

        # Show stats
        print("\n📊 Database Stats:")
        cursor.execute("SELECT COUNT(*) FROM deposits")
        deposit_count = cursor.fetchone()[0]
        print(f"   • Total deposits: {deposit_count}")

        cursor.execute("SELECT COUNT(*) FROM blacklist")
        blacklist_count = cursor.fetchone()[0]
        print(f"   • Blacklisted TXIDs: {blacklist_count}")

        print("\n✨ Database is ready for production!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    if not Path(DB_PATH).exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("Please run this script from the Convertbot directory")
        sys.exit(1)

    print("🗄️  Convertbot Database Migration")
    print("="*60)
    print(f"Database: {DB_PATH}")
    print("="*60)

    response = input("\nProceed with migration? (yes/no): ")
    if response.lower() != "yes":
        print("❌ Migration cancelled")
        sys.exit(0)

    run_migration()
