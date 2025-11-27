#!/bin/bash
# Health Check Script for Convertbot
# Checks services and sends alerts if issues found

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ALERT_FILE="/tmp/convertbot_alert_sent"

# Load environment for Telegram alerts
if [ -f "${PROJECT_DIR}/.env" ]; then
    source "${PROJECT_DIR}/.env"
fi

send_alert() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    echo "[$timestamp] ALERT: $message"

    # Send Telegram alert if token is set
    if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${ADMIN_CHAT_ID:-}" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${ADMIN_CHAT_ID}" \
            -d "text=🚨 CONVERTBOT ALERT\n\n${message}\n\nTime: ${timestamp}" \
            > /dev/null 2>&1 || true
    fi
}

check_passed=true
issues=""

# Check if bot service is running
if ! systemctl is-active --quiet convertbot-bot 2>/dev/null; then
    issues="${issues}\n❌ Bot service is DOWN"
    check_passed=false
fi

# Check if worker service is running
if ! systemctl is-active --quiet convertbot-worker 2>/dev/null; then
    issues="${issues}\n❌ Worker service is DOWN"
    check_passed=false
fi

# Check database file exists and is not corrupted
DB_FILE="${PROJECT_DIR}/swapbot.db"
if [ -f "$DB_FILE" ]; then
    if ! sqlite3 "$DB_FILE" "SELECT 1;" > /dev/null 2>&1; then
        issues="${issues}\n❌ Database corrupted or locked"
        check_passed=false
    fi
else
    issues="${issues}\n❌ Database file missing"
    check_passed=false
fi

# Check disk space (alert if less than 10%)
DISK_USAGE=$(df -h "$PROJECT_DIR" | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$DISK_USAGE" -gt 90 ]; then
    issues="${issues}\n⚠️ Disk usage critical: ${DISK_USAGE}%"
    check_passed=false
fi

# Check for stuck transactions (more than 2 hours in CONFIRMING)
STUCK_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM deposits WHERE status='CONFIRMING' AND inserted_at < datetime('now', '-2 hours');" 2>/dev/null || echo "0")
if [ "$STUCK_COUNT" -gt 0 ]; then
    issues="${issues}\n⚠️ ${STUCK_COUNT} stuck transactions (>2h)"
fi

# Check for failed trades in last hour
FAILED_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM deposits WHERE status='TRADE_FAILED' AND inserted_at > datetime('now', '-1 hour');" 2>/dev/null || echo "0")
if [ "$FAILED_COUNT" -gt 3 ]; then
    issues="${issues}\n⚠️ ${FAILED_COUNT} failed trades in last hour"
    check_passed=false
fi

# Report status
if [ "$check_passed" = true ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ Health check passed"
    # Clear alert flag if it exists
    rm -f "$ALERT_FILE" 2>/dev/null || true
else
    # Only send alert if not already sent in last 30 minutes
    if [ ! -f "$ALERT_FILE" ] || [ $(find "$ALERT_FILE" -mmin +30 2>/dev/null | wc -l) -gt 0 ]; then
        send_alert "$issues"
        touch "$ALERT_FILE"
    fi
fi
