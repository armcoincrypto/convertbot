#!/bin/bash
# Database Restore Script for Convertbot
# Usage: ./restore_db.sh [backup_file.db.gz]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DB_FILE="${PROJECT_DIR}/swapbot.db"
BACKUP_DIR="${PROJECT_DIR}/backups"

# Show available backups if no argument
if [ $# -eq 0 ]; then
    echo "Available backups:"
    echo "=================="
    ls -lht "$BACKUP_DIR"/swapbot_*.db.gz 2>/dev/null || echo "No backups found"
    echo ""
    echo "Usage: $0 <backup_file.db.gz>"
    echo "Example: $0 ${BACKUP_DIR}/swapbot_20250101_120000.db.gz"
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Stop services before restore
echo "⚠️  WARNING: This will replace the current database!"
echo "Backup file: $BACKUP_FILE"
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo "Stopping services..."
systemctl stop convertbot-bot 2>/dev/null || true
systemctl stop convertbot-worker 2>/dev/null || true

# Backup current database before restore
if [ -f "$DB_FILE" ]; then
    CURRENT_BACKUP="${BACKUP_DIR}/swapbot_pre_restore_$(date +%Y%m%d_%H%M%S).db"
    echo "Backing up current database to: $CURRENT_BACKUP"
    cp "$DB_FILE" "$CURRENT_BACKUP"
fi

# Restore from backup
echo "Restoring from backup..."
gunzip -c "$BACKUP_FILE" > "$DB_FILE"

# Verify restored database
echo "Verifying restored database..."
sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM deposits;" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Database restored and verified successfully"
else
    echo "❌ Database verification failed!"
    if [ -f "$CURRENT_BACKUP" ]; then
        echo "Restoring previous database..."
        cp "$CURRENT_BACKUP" "$DB_FILE"
    fi
    exit 1
fi

# Restart services
echo "Restarting services..."
systemctl start convertbot-bot 2>/dev/null || true
systemctl start convertbot-worker 2>/dev/null || true

echo "✅ Restore complete!"
echo "Current database stats:"
sqlite3 "$DB_FILE" "SELECT 'Deposits:', COUNT(*) FROM deposits; SELECT 'Users:', COUNT(*) FROM users;"
