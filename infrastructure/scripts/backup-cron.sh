#!/bin/bash
# =============================================================================
# SecureGit automated backup cron script
# Install as root crontab: 0 2 * * * /usr/local/bin/securegit-backup-cron.sh
# =============================================================================
set -euo pipefail

FLASK_URL="http://127.0.0.1:5000"
# Use a service token or admin credentials stored securely
# For simplicity: call the internal backup API directly
BACKUP_DEST="/mnt/backup"

# Trigger backup via Flask API (internal call)
curl -s -f -X POST \
    "$FLASK_URL/api/backups" \
    -H "Content-Type: application/json" \
    -d "{\"backup_type\": \"full\", \"destination\": \"$BACKUP_DEST\"}" \
    --max-time 30 \
    > /var/log/securegit/backup-cron.log 2>&1

# Remove backups older than 30 days
find "$BACKUP_DEST" -name "securegit_*.tar.gz" -mtime +30 -delete || true
find "$BACKUP_DEST" -name "securegit_*.sql.gz" -mtime +30 -delete || true

echo "$(date): Backup cron completed." >> /var/log/securegit/backup-cron.log
