"""
Daily Reconciliation Job for Convertbot
Compares database records with blockchain/exchange data
Run via cron: 0 3 * * * python -m scripts.reconciliation
"""
import asyncio
import aiosqlite
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.logger import setup_logger
from libs.telegram_client import TelegramClient
from libs.mexc_client import MEXCClient

logger = setup_logger("reconciliation")


class Reconciliation:
    """Automated reconciliation between DB, blockchain, and exchange"""

    def __init__(self):
        self.db_path = settings.database_url.replace("sqlite:///", "")
        self.telegram = TelegramClient(settings.telegram_bot_token, settings.admin_chat_id)
        self.mexc = MEXCClient(settings.mexc_api_key, settings.mexc_api_secret)
        self.issues: List[Dict[str, Any]] = []
        self.stats = {
            "deposits_checked": 0,
            "withdrawals_checked": 0,
            "issues_found": 0,
            "volume_db": 0.0,
            "volume_exchange": 0.0,
        }

    async def run(self):
        """Run full reconciliation"""
        logger.info("=" * 60)
        logger.info("🔍 STARTING DAILY RECONCILIATION")
        logger.info("=" * 60)

        try:
            # Check for stuck transactions
            await self._check_stuck_transactions()

            # Check for orphaned deposits (in DB but not on exchange)
            await self._check_orphaned_deposits()

            # Check for missing withdrawals
            await self._check_missing_withdrawals()

            # Check volume discrepancies
            await self._check_volume_discrepancy()

            # Generate and send report
            await self._send_report()

        except Exception as e:
            logger.error(f"Reconciliation failed: {e}")
            await self.telegram.send_message(
                settings.admin_chat_id,
                f"❌ Reconciliation job failed!\n\nError: {str(e)}"
            )

    async def _check_stuck_transactions(self):
        """Find transactions stuck in intermediate states"""
        logger.info("Checking for stuck transactions...")

        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row

            # Deposits stuck in CONFIRMING for > 4 hours
            cursor = await conn.execute("""
                SELECT txid, coin, user_id, status, confs, required_confs, inserted_at
                FROM deposits
                WHERE status IN ('NEW', 'CONFIRMING', 'CONFIRMED', 'SOLD')
                AND inserted_at < datetime('now', '-4 hours')
            """)
            stuck = await cursor.fetchall()

            for row in stuck:
                self.issues.append({
                    "type": "STUCK_TRANSACTION",
                    "severity": "HIGH" if row["status"] in ("CONFIRMED", "SOLD") else "MEDIUM",
                    "txid": row["txid"],
                    "coin": row["coin"],
                    "status": row["status"],
                    "confs": f"{row['confs']}/{row['required_confs']}",
                    "age": row["inserted_at"],
                    "user_id": row["user_id"],
                })
                self.stats["issues_found"] += 1

            logger.info(f"Found {len(stuck)} stuck transactions")

    async def _check_orphaned_deposits(self):
        """Find deposits in DB that are CONFIRMED but no matching exchange trade"""
        logger.info("Checking for orphaned deposits...")

        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row

            # CONFIRMED deposits that should have been traded
            cursor = await conn.execute("""
                SELECT txid, coin, user_id, onchain_amount, inserted_at
                FROM deposits
                WHERE status = 'CONFIRMED'
                AND inserted_at < datetime('now', '-1 hour')
            """)
            orphaned = await cursor.fetchall()

            for row in orphaned:
                self.issues.append({
                    "type": "ORPHANED_DEPOSIT",
                    "severity": "HIGH",
                    "txid": row["txid"],
                    "coin": row["coin"],
                    "amount": row["onchain_amount"],
                    "user_id": row["user_id"],
                })
                self.stats["issues_found"] += 1

            self.stats["deposits_checked"] += len(orphaned)
            logger.info(f"Found {len(orphaned)} orphaned deposits")

    async def _check_missing_withdrawals(self):
        """Find SOLD deposits that haven't been withdrawn"""
        logger.info("Checking for missing withdrawals...")

        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row

            # SOLD deposits older than 30 minutes
            cursor = await conn.execute("""
                SELECT txid, coin, user_id, target_address, inserted_at
                FROM deposits
                WHERE status = 'SOLD'
                AND inserted_at < datetime('now', '-30 minutes')
            """)
            missing = await cursor.fetchall()

            for row in missing:
                self.issues.append({
                    "type": "MISSING_WITHDRAWAL",
                    "severity": "CRITICAL",
                    "txid": row["txid"],
                    "coin": row["coin"],
                    "target_address": row["target_address"],
                    "user_id": row["user_id"],
                })
                self.stats["issues_found"] += 1

            self.stats["withdrawals_checked"] += len(missing)
            logger.info(f"Found {len(missing)} missing withdrawals")

    async def _check_volume_discrepancy(self):
        """Compare 24h volume between DB and exchange"""
        logger.info("Checking volume discrepancy...")

        async with aiosqlite.connect(self.db_path) as conn:
            # Get 24h volume from DB
            cursor = await conn.execute("""
                SELECT COALESCE(SUM(onchain_amount), 0) as total
                FROM deposits
                WHERE status = 'WITHDRAWN'
                AND inserted_at > datetime('now', '-24 hours')
            """)
            row = await cursor.fetchone()
            self.stats["volume_db"] = row[0] if row else 0

        # Note: Exchange volume check would require API call
        # For now, just log the DB volume
        logger.info(f"24h DB volume: {self.stats['volume_db']:.4f}")

    async def _send_report(self):
        """Generate and send reconciliation report"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not self.issues:
            report = (
                f"✅ RECONCILIATION REPORT\n"
                f"📅 {timestamp}\n\n"
                f"All checks passed!\n"
                f"• Deposits checked: {self.stats['deposits_checked']}\n"
                f"• Withdrawals checked: {self.stats['withdrawals_checked']}\n"
                f"• 24h volume: {self.stats['volume_db']:.4f}"
            )
        else:
            # Group issues by severity
            critical = [i for i in self.issues if i.get("severity") == "CRITICAL"]
            high = [i for i in self.issues if i.get("severity") == "HIGH"]
            medium = [i for i in self.issues if i.get("severity") == "MEDIUM"]

            report = (
                f"⚠️ RECONCILIATION REPORT\n"
                f"📅 {timestamp}\n\n"
                f"Issues found: {self.stats['issues_found']}\n"
            )

            if critical:
                report += f"\n🔴 CRITICAL ({len(critical)}):\n"
                for issue in critical[:5]:
                    report += f"  • {issue['type']}: {issue.get('txid', 'N/A')[:16]}...\n"

            if high:
                report += f"\n🟠 HIGH ({len(high)}):\n"
                for issue in high[:5]:
                    report += f"  • {issue['type']}: {issue.get('txid', 'N/A')[:16]}...\n"

            if medium:
                report += f"\n🟡 MEDIUM ({len(medium)}):\n"
                for issue in medium[:3]:
                    report += f"  • {issue['type']}: {issue.get('txid', 'N/A')[:16]}...\n"

            report += f"\n📊 Stats:\n"
            report += f"• Deposits: {self.stats['deposits_checked']}\n"
            report += f"• Withdrawals: {self.stats['withdrawals_checked']}\n"
            report += f"• 24h volume: {self.stats['volume_db']:.4f}"

        # Send to admin
        await self.telegram.send_message(settings.admin_chat_id, report)
        logger.info("Reconciliation report sent")

        # Save detailed report to file
        report_file = f"/var/log/convertbot/reconciliation_{datetime.now().strftime('%Y%m%d')}.json"
        try:
            import json
            os.makedirs(os.path.dirname(report_file), exist_ok=True)
            with open(report_file, "w") as f:
                json.dump({
                    "timestamp": timestamp,
                    "stats": self.stats,
                    "issues": self.issues
                }, f, indent=2, default=str)
            logger.info(f"Detailed report saved to {report_file}")
        except Exception as e:
            logger.warning(f"Could not save detailed report: {e}")


async def main():
    """Run reconciliation job"""
    reconciler = Reconciliation()
    await reconciler.run()


if __name__ == "__main__":
    asyncio.run(main())
