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
        output_coin=row['output_coin'] if 'output_coin' in row.keys() else 'USDT',
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
                output_coin TEXT DEFAULT 'USDT'
            )
        """)
        # Add output_coin column if it doesn't exist (migration)
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
        deposits.append(Deposit(
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
            output_coin=row['output_coin'] if 'output_coin' in row.keys() else 'USDT',
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
        output_coin=row['output_coin'] if 'output_coin' in row.keys() else 'USDT',
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
            deposits.append(Deposit(
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
                output_coin=row['output_coin'] if 'output_coin' in row.keys() else 'USDT',
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


# ==================== REFERRAL SYSTEM ====================

import random
import string

def generate_referral_code() -> str:
    """Generate unique referral code like REF12345678"""
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(chars, k=8))
    return f"REF{random_part}"


async def init_referral_tables():
    """Initialize referral system tables"""
    async with aiosqlite.connect(get_db_path()) as conn:
        # Add referral columns to users table
        try:
            await conn.execute("ALTER TABLE users ADD COLUMN referral_code TEXT UNIQUE")
        except:
            pass
        try:
            await conn.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER")
        except:
            pass
        try:
            await conn.execute("ALTER TABLE users ADD COLUMN referral_balance REAL DEFAULT 0")
        except:
            pass
        try:
            await conn.execute("ALTER TABLE users ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")
        except:
            pass

        # Create referral earnings log table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS referral_earnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER NOT NULL,
                deposit_txid TEXT NOT NULL,
                swap_amount REAL NOT NULL,
                our_fee REAL NOT NULL,
                referrer_cut REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create referral bonuses table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS referral_bonuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                bonus_type TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await conn.commit()
    logger.info("Referral tables initialized")


async def get_or_create_referral_code(user_id: int) -> str:
    """Get user's referral code or create one"""
    async with aiosqlite.connect(get_db_path()) as conn:
        # Check if user has a code
        async with conn.execute(
            "SELECT referral_code FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

        if row and row[0]:
            return row[0]

        # Generate new unique code
        for _ in range(10):  # Try up to 10 times
            code = generate_referral_code()
            try:
                await conn.execute(
                    "UPDATE users SET referral_code = ? WHERE user_id = ?",
                    (code, user_id)
                )
                await conn.commit()
                return code
            except:
                continue

        # Fallback: use user_id based code
        code = f"REF{user_id}"
        await conn.execute(
            "UPDATE users SET referral_code = ? WHERE user_id = ?",
            (code, user_id)
        )
        await conn.commit()
        return code


async def get_user_by_referral_code(code: str) -> Optional[int]:
    """Get user_id by referral code"""
    async with aiosqlite.connect(get_db_path()) as conn:
        async with conn.execute(
            "SELECT user_id FROM users WHERE referral_code = ?", (code,)
        ) as cursor:
            row = await cursor.fetchone()
    return row[0] if row else None


async def set_user_referrer(user_id: int, referrer_id: int) -> bool:
    """Set who referred this user (only if not already set)"""
    if user_id == referrer_id:
        return False  # Can't refer yourself

    async with aiosqlite.connect(get_db_path()) as conn:
        # Check if already has referrer
        async with conn.execute(
            "SELECT referred_by FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

        if row and row[0]:
            return False  # Already has referrer

        await conn.execute(
            "UPDATE users SET referred_by = ? WHERE user_id = ?",
            (referrer_id, user_id)
        )
        await conn.commit()
        logger.info(f"User {user_id} referred by {referrer_id}")
        return True


async def get_user_referrer(user_id: int) -> Optional[int]:
    """Get referrer user_id for a user"""
    async with aiosqlite.connect(get_db_path()) as conn:
        async with conn.execute(
            "SELECT referred_by FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
    return row[0] if row and row[0] else None


async def add_referral_earning(referrer_id: int, referred_id: int, txid: str,
                                swap_amount: float, our_fee: float, referrer_cut: float) -> None:
    """Record a referral earning"""
    async with aiosqlite.connect(get_db_path()) as conn:
        # Add to earnings log
        await conn.execute("""
            INSERT INTO referral_earnings
            (referrer_id, referred_id, deposit_txid, swap_amount, our_fee, referrer_cut)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (referrer_id, referred_id, txid, swap_amount, our_fee, referrer_cut))

        # Update referrer's balance
        await conn.execute(
            "UPDATE users SET referral_balance = referral_balance + ? WHERE user_id = ?",
            (referrer_cut, referrer_id)
        )
        await conn.commit()
    logger.info(f"Referral earning: {referrer_id} earned ${referrer_cut:.2f} from {referred_id}")


async def get_referral_stats(user_id: int) -> dict:
    """Get referral statistics for a user"""
    async with aiosqlite.connect(get_db_path()) as conn:
        # Get balance
        async with conn.execute(
            "SELECT referral_balance FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
        balance = row[0] if row and row[0] else 0

        # Count active referrals (users who completed at least 1 swap)
        async with conn.execute("""
            SELECT COUNT(DISTINCT u.user_id)
            FROM users u
            JOIN deposits d ON u.user_id = d.user_id
            WHERE u.referred_by = ? AND d.status = 'WITHDRAWN'
        """, (user_id,)) as cursor:
            row = await cursor.fetchone()
        active_referrals = row[0] if row else 0

        # Total referrals (all users referred, even without swaps)
        async with conn.execute(
            "SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
        total_referrals = row[0] if row else 0

        # Total earned
        async with conn.execute(
            "SELECT SUM(referrer_cut) FROM referral_earnings WHERE referrer_id = ?",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
        total_earned = row[0] if row and row[0] else 0

        # Get bonuses claimed
        async with conn.execute(
            "SELECT bonus_type FROM referral_bonuses WHERE user_id = ?", (user_id,)
        ) as cursor:
            bonuses = [row[0] for row in await cursor.fetchall()]

    return {
        'balance': balance,
        'active_referrals': active_referrals,
        'total_referrals': total_referrals,
        'total_earned': total_earned,
        'bonuses_claimed': bonuses
    }


async def check_and_award_bonus(user_id: int) -> Optional[tuple]:
    """Check if user earned a milestone bonus and award it"""
    stats = await get_referral_stats(user_id)
    active = stats['active_referrals']
    claimed = stats['bonuses_claimed']

    bonus_to_award = None

    if active >= 200 and '200_REFERRALS' not in claimed:
        bonus_to_award = ('200_REFERRALS', 200.0)
    elif active >= 50 and '50_REFERRALS' not in claimed:
        bonus_to_award = ('50_REFERRALS', 50.0)

    if bonus_to_award:
        async with aiosqlite.connect(get_db_path()) as conn:
            await conn.execute("""
                INSERT INTO referral_bonuses (user_id, bonus_type, amount)
                VALUES (?, ?, ?)
            """, (user_id, bonus_to_award[0], bonus_to_award[1]))

            await conn.execute(
                "UPDATE users SET referral_balance = referral_balance + ? WHERE user_id = ?",
                (bonus_to_award[1], user_id)
            )
            await conn.commit()
        logger.info(f"Awarded {bonus_to_award[0]} bonus (${bonus_to_award[1]}) to user {user_id}")
        return bonus_to_award

    return None


async def ensure_user_exists(user_id: int) -> None:
    """Make sure user exists in database with a referral code"""
    async with aiosqlite.connect(get_db_path()) as conn:
        async with conn.execute(
            "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            code = generate_referral_code()
            await conn.execute(
                "INSERT INTO users (user_id, usdt_trc20_address, referral_code) VALUES (?, '', ?)",
                (user_id, code)
            )
            await conn.commit()
            logger.info(f"Created user {user_id} with referral code {code}")
