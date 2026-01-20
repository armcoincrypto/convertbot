"""Database layer with SQLite support."""
import aiosqlite
from typing import List, Optional
from datetime import datetime
from app.models import Deposit, DepositStatus, CoinType, User
from app.logger import setup_logger
from app.config import settings

DB_PATH = "swapbot.db"

logger = setup_logger(__name__)


def get_db_path():
    """Get database path from config."""
    db_url = settings.database_url
    if db_url.startswith('sqlite'):
        return db_url.replace('sqlite:///', '')
    return 'swapbot.db'


def _row_to_deposit(row) -> "Deposit":
    """Convert database row to Deposit object"""
    from app.models import Deposit, DepositStatus, CoinType
    return Deposit(
        txid=row['txid'],
        coin=CoinType(row['coin']),
        user_id=row['user_id'],
        target_address=row['target_address'],
        status=DepositStatus(row['status']),
        confs=row['confs'],
        required_confs=row['required_confs'],
        onchain_amount=row['onchain_amount'] if row['onchain_amount'] else 0.0,
        usdt_amount=row['usdt_amount'] if row['usdt_amount'] is not None else None,
        final_usdt=row['final_usdt'] if row['final_usdt'] is not None else None,
    )


async def init_db():
    """Initialize database schema."""
    async with aiosqlite.connect(get_db_path()) as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS deposits (
                txid TEXT PRIMARY KEY,
                coin TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                status TEXT DEFAULT 'NEW',
                confs INTEGER DEFAULT 0,
                required_confs INTEGER,
                inserted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                target_address TEXT,
                onchain_amount REAL,
                usdt_amount REAL,
                final_usdt REAL,
                output_coin TEXT DEFAULT 'USDT',
                retry_count INTEGER DEFAULT 0
            )
        """)
        # Add retry_count column if missing (for existing databases)
        try:
            await conn.execute("ALTER TABLE deposits ADD COLUMN retry_count INTEGER DEFAULT 0")
        except:
            pass  # Column already exists
        # Add output_coin column if missing
        try:
            await conn.execute("ALTER TABLE deposits ADD COLUMN output_coin TEXT DEFAULT 'USDT'")
        except:
            pass  # Column already exists
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                usdt_trc20_address TEXT NOT NULL
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS withdrawals (
                txid TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                coin TEXT NOT NULL,
                amount REAL NOT NULL,
                address TEXT NOT NULL,
                withdraw_id TEXT,
                fee REAL,
                status TEXT DEFAULT 'PENDING',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.commit()
    logger.info("Database initialized")


async def get_pending_deposits(statuses: List[DepositStatus] = None) -> List[Deposit]:
    """Fetch pending deposits."""
    if statuses is None:
        statuses = [DepositStatus.NEW, DepositStatus.CONFIRMING, DepositStatus.CONFIRMED, DepositStatus.SOLD]
    
    status_values = [s.value for s in statuses]
    placeholders = ','.join(['?' for _ in status_values])
    
    async with aiosqlite.connect(get_db_path()) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            f"SELECT * FROM deposits WHERE status IN ({placeholders}) ORDER BY inserted_at",
            status_values
        ) as cursor:
            rows = await cursor.fetchall()
    
    deposits = []
    for row in rows:
        # Safe column access for optional columns
        try:
            usdt_amt = row['usdt_amount'] if row['usdt_amount'] else None
        except (KeyError, IndexError):
            usdt_amt = None
        try:
            final_amt = row['final_usdt'] if row['final_usdt'] else None
        except (KeyError, IndexError):
            final_amt = None

        deposits.append(Deposit(
            txid=row['txid'],
            coin=CoinType(row['coin']),
            user_id=row['user_id'],
            status=DepositStatus(row['status']),
            confs=row['confs'],
            required_confs=row['required_confs'],
            target_address=row['target_address'],
            onchain_amount=row['onchain_amount'] if row['onchain_amount'] else None,
            usdt_amount=usdt_amt,
            final_usdt=final_amt,
        ))
    return deposits


async def get_deposits_by_status(status: DepositStatus) -> List[Deposit]:
    """Get all deposits with a specific status"""
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM deposits WHERE status = ? ORDER BY inserted_at DESC""",
            (status.value,)
        )
        rows = await cursor.fetchall()
        return [_row_to_deposit(row) for row in rows]


async def update_deposit_status(txid: str, status: DepositStatus, confs: Optional[int] = None) -> None:
    """Update deposit status."""
    async with aiosqlite.connect(get_db_path()) as conn:
        if confs is not None:
            await conn.execute(
                "UPDATE deposits SET status = ?, confs = ?, updated_at = ? WHERE txid = ?",
                (status.value, confs, datetime.utcnow().isoformat(), txid)
            )
        else:
            await conn.execute(
                "UPDATE deposits SET status = ?, updated_at = ? WHERE txid = ?",
                (status.value, datetime.utcnow().isoformat(), txid)
            )
        await conn.commit()
    logger.info(f"Updated deposit {txid} to {status.value}")


async def update_deposit_confs(txid: str, confs: int):
    """Update deposit confirmations"""
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "UPDATE deposits SET confs = ?, updated_at = ? WHERE txid = ?",
            (confs, datetime.utcnow().isoformat(), txid)
        )
        await db.commit()
    logger.info(f"Updated deposit {txid[:16]}... confirmations: {confs}")


async def get_user(user_id: int) -> Optional[User]:
    """Fetch user by ID."""
    async with aiosqlite.connect(get_db_path()) as conn:
        async with conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
    if not row:
        return None
    return User(user_id=row[0], usdt_trc20_address=row[1])


async def insert_user(user_id: int, usdt_address: str) -> None:
    """Insert a new user."""
    async with aiosqlite.connect(get_db_path()) as conn:
        await conn.execute(
            "INSERT OR IGNORE INTO users (user_id, usdt_trc20_address) VALUES (?, ?)",
            (user_id, usdt_address)
        )
        await conn.commit()
    logger.info(f"Inserted user {user_id}")


async def insert_deposit(txid: str, coin: CoinType, user_id: int, required_confs: int, 
                        target_address: str, amount: float = None) -> None:
    """Insert a new deposit."""
    async with aiosqlite.connect(get_db_path()) as conn:
        await conn.execute(
            """INSERT OR IGNORE INTO deposits 
               (txid, coin, user_id, status, confs, required_confs, target_address, onchain_amount) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (txid, coin.value, user_id, DepositStatus.NEW.value, 0, required_confs, target_address, amount)
        )
        await conn.commit()
    logger.info(f"Inserted deposit {txid}")


async def update_deposit_amount(txid: str, amount: float) -> None:
    """Update deposit amount."""
    async with aiosqlite.connect(get_db_path()) as conn:
        await conn.execute(
            "UPDATE deposits SET onchain_amount = ?, updated_at = ? WHERE txid = ?",
            (amount, datetime.utcnow().isoformat(), txid)
        )
        await conn.commit()
    logger.info(f"Updated deposit {txid} amount: {amount}")


async def update_deposit_usdt(txid: str, usdt_amount: float, final_usdt: float):
    """Update USDT amounts for a deposit"""
    async with aiosqlite.connect(get_db_path()) as conn:
        await conn.execute(
            "UPDATE deposits SET usdt_amount = ?, final_usdt = ?, updated_at = ? WHERE txid = ?",
            (usdt_amount, final_usdt, datetime.utcnow().isoformat(), txid)
        )
        await conn.commit()
    logger.info(f"Updated deposit {txid[:16]}... USDT: {usdt_amount:.2f} → {final_usdt:.2f}")


async def get_deposit(txid: str) -> Optional[Deposit]:
    """Get deposit by txid."""
    async with aiosqlite.connect(get_db_path()) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM deposits WHERE txid = ?", (txid,)) as cursor:
            row = await cursor.fetchone()
    
    if not row:
        return None
    
    return Deposit(
        txid=row['txid'],
        coin=CoinType(row['coin']),
        user_id=row['user_id'],
        status=DepositStatus(row['status']),
        confs=row['confs'],
        required_confs=row['required_confs'],
        target_address=row['target_address'],
        onchain_amount=row['onchain_amount'] if row['onchain_amount'] else None,
        usdt_amount=row['usdt_amount'] if row['usdt_amount'] is not None else None,
        final_usdt=row['final_usdt'] if row['final_usdt'] is not None else None,
    )


async def txid_exists(txid: str) -> bool:
    """Check if TXID already exists in database"""
    async with aiosqlite.connect(get_db_path()) as conn:
        async with conn.execute("SELECT 1 FROM deposits WHERE txid = ?", (txid,)) as cursor:
            row = await cursor.fetchone()
    return row is not None


async def get_txid_owner(txid: str) -> Optional[int]:
    """Get user_id who owns this TXID"""
    async with aiosqlite.connect(get_db_path()) as conn:
        async with conn.execute("SELECT user_id FROM deposits WHERE txid = ?", (txid,)) as cursor:
            row = await cursor.fetchone()
    return row[0] if row else None


async def get_user_deposits(user_id: int, limit: int = 10) -> List[Deposit]:
    """Get deposits for a specific user"""
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM deposits WHERE user_id = ? ORDER BY inserted_at DESC LIMIT ?",
            (user_id, limit)
        )
        rows = await cursor.fetchall()
        
        deposits = []
        for row in rows:
            # Safe column access for optional columns
            try:
                usdt_amt = row['usdt_amount'] if row['usdt_amount'] else None
            except (KeyError, IndexError):
                usdt_amt = None
            try:
                final_amt = row['final_usdt'] if row['final_usdt'] else None
            except (KeyError, IndexError):
                final_amt = None

            deposits.append(Deposit(
                txid=row['txid'],
                coin=CoinType(row['coin']),
                user_id=row['user_id'],
                status=DepositStatus(row['status']),
                confs=row['confs'],
                required_confs=row['required_confs'],
                target_address=row['target_address'],
                onchain_amount=row['onchain_amount'] if row['onchain_amount'] else None,
                usdt_amount=usdt_amt,
                final_usdt=final_amt,
            ))

        return deposits


async def create_withdrawal(txid: str, user_id: int, coin: str, amount: float, 
                            address: str, withdraw_id: str, fee: float) -> None:
    """Create withdrawal record"""
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("""
            INSERT OR IGNORE INTO withdrawals 
            (txid, user_id, coin, amount, address, withdraw_id, fee, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', CURRENT_TIMESTAMP)
        """, (txid, user_id, coin, amount, address, withdraw_id, fee))
        await db.commit()
        logger.info(f"Created withdrawal record: {withdraw_id}")


async def add_withdrawal_info(txid: str, withdrawal_id: str, amount_usdt: float,
                              final_amount: float, fee: float, trade_order_id: str) -> None:
    """Record withdrawal details."""
    async with aiosqlite.connect(get_db_path()) as conn:
        await conn.execute("""
            INSERT OR REPLACE INTO withdrawals (txid, withdrawal_id, amount_usdt, final_amount, fee, trade_order_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (txid, withdrawal_id, amount_usdt, final_amount, fee, trade_order_id))
        await conn.commit()
    logger.info(f"Added withdrawal info for {txid}")


async def get_retry_count(txid: str) -> int:
    """Get retry count for a deposit."""
    async with aiosqlite.connect(get_db_path()) as conn:
        async with conn.execute(
            "SELECT retry_count FROM deposits WHERE txid = ?", (txid,)
        ) as cursor:
            row = await cursor.fetchone()
    return row[0] if row and row[0] else 0


async def increment_retry_count(txid: str) -> int:
    """Increment retry count and return new value."""
    async with aiosqlite.connect(get_db_path()) as conn:
        await conn.execute(
            "UPDATE deposits SET retry_count = COALESCE(retry_count, 0) + 1, updated_at = ? WHERE txid = ?",
            (datetime.utcnow().isoformat(), txid)
        )
        await conn.commit()
        async with conn.execute(
            "SELECT retry_count FROM deposits WHERE txid = ?", (txid,)
        ) as cursor:
            row = await cursor.fetchone()
    new_count = row[0] if row else 1
    logger.info(f"Incremented retry count for {txid[:16]}... to {new_count}")
    return new_count


async def reset_retry_count(txid: str) -> None:
    """Reset retry count to 0."""
    async with aiosqlite.connect(get_db_path()) as conn:
        await conn.execute(
            "UPDATE deposits SET retry_count = 0, updated_at = ? WHERE txid = ?",
            (datetime.utcnow().isoformat(), txid)
        )
        await conn.commit()
    logger.info(f"Reset retry count for {txid[:16]}...")
