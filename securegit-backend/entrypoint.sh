#!/bin/bash
set -e

echo "=== Waiting for database to be ready ==="
# Wait for PostgreSQL to be reachable
for i in $(seq 1 30); do
    if pg_isready -h db -p 5432 -U securegit_app > /dev/null 2>&1; then
        echo "Database is ready!"
        break
    fi
    echo "Waiting for database... ($i/30)"
    sleep 2
done

echo "=== Running database migrations ==="
flask db upgrade || {
    echo "Migration failed, attempting to create tables directly..."
    python -c "
from app import create_app
from app.extensions import db
app = create_app()
with app.app_context():
    db.create_all()
    print('Tables created successfully via db.create_all()')
"
}

echo "=== Setting up environment for SSH ==="
# Provide INTERNAL_HOOK_SECRET to git-shell-wrapper since SSH scrubs env vars
echo "INTERNAL_HOOK_SECRET=${INTERNAL_HOOK_SECRET:-hook-secret-change}" > /app/.env
chown www-data:www-data /app/.env

echo "=== Starting SSH Daemon ==="
mkdir -p /home/git/.ssh
chown -R git:git /home/git/.ssh
chmod 700 /home/git/.ssh

echo "=== Syncing SSH Keys from DB ==="
python -c "
from app import create_app
from app.models.ssh_key import SSHKey
from app.services.ssh_service import rebuild_authorized_keys

app = create_app()
with app.app_context():
    keys = SSHKey.query.all()
    rebuild_authorized_keys([{'user_id': k.user_id, 'public_key': k.public_key, 'fingerprint': k.fingerprint} for k in keys])
    print(f'Synced {len(keys)} SSH keys to authorized_keys')
"

/usr/sbin/sshd

echo "=== Starting Gunicorn ==="
exec gunicorn --bind 0.0.0.0:5000 --workers 4 wsgi:app
