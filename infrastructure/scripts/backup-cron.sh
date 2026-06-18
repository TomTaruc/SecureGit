#!/bin/bash
# =============================================================================
# SecureGit automated backup cron script
# Install as root crontab: 0 2 * * * /usr/local/bin/securegit-backup-cron.sh
# =============================================================================
set -euo pipefail

FLASK_URL="http://127.0.0.1:5000"
BACKUP_DEST="/mnt/backup"
ENV_FILE="/opt/securegit/backend/.env"

if [ -f "$ENV_FILE" ]; then
    HOOK_SECRET=$(grep -E '^INTERNAL_HOOK_SECRET=' "$ENV_FILE" | cut -d '=' -f 2-)
else
    HOOK_SECRET=""
fi

# Trigger backup via Flask API (internal call)
curl -s -f -X POST \
    "$FLASK_URL/internal/backup" \
    -H "Content-Type: application/json" \
    -H "X-Hook-Secret: $HOOK_SECRET" \
    -d "{\"backup_type\": \"full\", \"destination\": \"$BACKUP_DEST\"}" \
    --max-time 30 \
    > /var/log/securegit/backup-cron.log 2>&1

# Remove backups older than 30 days
find "$BACKUP_DEST" -name "securegit_*.tar.gz" -mtime +30 -delete || true
find "$BACKUP_DEST" -name "securegit_*.sql.gz" -mtime +30 -delete || true

echo "$(date): Backup cron completed." >> /var/log/securegit/backup-cron.log
