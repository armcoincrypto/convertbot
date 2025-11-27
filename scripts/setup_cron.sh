#!/bin/bash
# Setup cron jobs for Convertbot
# Run: sudo ./setup_cron.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Setting up cron jobs for Convertbot..."

# Create cron file
CRON_FILE="/etc/cron.d/convertbot"

cat > "$CRON_FILE" << EOF
# Convertbot automated tasks
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# Database backup every 6 hours
0 */6 * * * root ${SCRIPT_DIR}/backup_db.sh >> /var/log/convertbot/backup.log 2>&1

# Reconciliation check daily at 3 AM
0 3 * * * root cd ${PROJECT_DIR} && ${PROJECT_DIR}/venv/bin/python -m scripts.reconciliation >> /var/log/convertbot/reconciliation.log 2>&1

# Health check every 5 minutes
*/5 * * * * root ${SCRIPT_DIR}/health_check.sh >> /var/log/convertbot/health.log 2>&1
EOF

chmod 644 "$CRON_FILE"

echo "✅ Cron jobs installed:"
echo "   - DB backup: every 6 hours"
echo "   - Reconciliation: daily at 3 AM"
echo "   - Health check: every 5 minutes"
echo ""
echo "View cron file: cat $CRON_FILE"
