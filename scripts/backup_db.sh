#!/bin/bash
# Automated Database Backup Script for Convertbot
# Run via cron: 0 */6 * * * /root/Convertbot/scripts/backup_db.sh

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DB_FILE="${PROJECT_DIR}/swapbot.db"
BACKUP_DIR="${PROJECT_DIR}/backups"
RETENTION_DAYS=30
MAX_BACKUPS=50

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

# Generate backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/swapbot_${TIMESTAMP}.db"

# Check if database exists
if [ ! -f "$DB_FILE" ]; then
    echo "ERROR: Database file not found: $DB_FILE"
    exit 1
fi

# Create backup using SQLite's backup command (safe for concurrent access)
echo "Creating backup: $BACKUP_FILE"
sqlite3 "$DB_FILE" ".backup '$BACKUP_FILE'"

# Compress the backup
echo "Compressing backup..."
gzip "$BACKUP_FILE"
BACKUP_FILE="${BACKUP_FILE}.gz"

# Calculate backup size
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Backup created: $BACKUP_FILE ($BACKUP_SIZE)"

# Cleanup old backups (older than RETENTION_DAYS)
echo "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "swapbot_*.db.gz" -type f -mtime +$RETENTION_DAYS -delete

# Also limit total number of backups
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/swapbot_*.db.gz 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt "$MAX_BACKUPS" ]; then
    echo "Removing oldest backups (keeping $MAX_BACKUPS)..."
    ls -1t "$BACKUP_DIR"/swapbot_*.db.gz | tail -n +$((MAX_BACKUPS + 1)) | xargs rm -f
fi

# Verify backup integrity
echo "Verifying backup integrity..."
gunzip -c "$BACKUP_FILE" | sqlite3 ":memory:" ".tables" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Backup verified successfully"
else
    echo "❌ Backup verification failed!"
    exit 1
fi

# Log backup event
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup completed: $BACKUP_FILE ($BACKUP_SIZE)" >> "${BACKUP_DIR}/backup.log"

echo "Backup complete!"
