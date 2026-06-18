#!/bin/bash
# =============================================================================
# SecureGit Server Setup Script
# Run as root on Ubuntu Server 26.04 LTS
# Usage: sudo bash setup-server.sh [SERVER_IP] [ADMIN_PASSWORD]
# =============================================================================
set -euo pipefail

SERVER_IP="${1:-192.168.1.100}"
ADMIN_PASSWORD="${2:-changeme123}"
REPO_DIR="/opt/securegit"
GIT_BASE="/srv/git"
VENV_DIR="$REPO_DIR/venv"
WWW_DIR="/var/www/securegit"
LOG_DIR="/var/log/securegit"

echo "=============================="
echo " SecureGit Server Setup"
echo " Server IP: $SERVER_IP"
echo "=============================="

# ---------------------------------------------------------------------------
# 1. Install dependencies
# ---------------------------------------------------------------------------
apt-get update -q
apt-get install -y --no-install-recommends \
    git nginx postgresql postgresql-contrib \
    python3 python3-pip python3-venv python3-dev \
    nodejs npm dnsmasq openssl curl ufw \
    libpq-dev build-essential

# Install NVM + Node LTS (optional, if apt nodejs is old)
# curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash

# ---------------------------------------------------------------------------
# 2. Create git system user
# ---------------------------------------------------------------------------
if ! id -u git &>/dev/null; then
    adduser --system --shell /usr/bin/git-shell --gecos "Git Service" --group git
    echo "Created 'git' system user."
fi
mkdir -p /home/git/.ssh
chmod 700 /home/git/.ssh
touch /home/git/.ssh/authorized_keys
chmod 600 /home/git/.ssh/authorized_keys
chown -R git:git /home/git/.ssh

# ---------------------------------------------------------------------------
# 3. Create chroot jail base structure
# ---------------------------------------------------------------------------
mkdir -p "$GIT_BASE"
chown root:root "$GIT_BASE"
chmod 755 "$GIT_BASE"

# ---------------------------------------------------------------------------
# 4. PostgreSQL setup
# ---------------------------------------------------------------------------
DB_USER="securegit_app"
DB_NAME="securegit_db"
DB_PASS=$(openssl rand -hex 24)

sudo -u postgres psql <<SQL
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
        CREATE ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASS';
    END IF;
END \$\$;

SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME') \gexec

GRANT CONNECT ON DATABASE $DB_NAME TO $DB_USER;
GRANT USAGE ON SCHEMA public TO $DB_USER;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO $DB_USER;
SQL

echo "PostgreSQL database '$DB_NAME' and role '$DB_USER' configured."

# ---------------------------------------------------------------------------
# 5. Deploy Flask backend
# ---------------------------------------------------------------------------
mkdir -p "$REPO_DIR/backend"
cp -r "$(dirname "$0")/../../securegit-backend/." "$REPO_DIR/backend/"

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r "$REPO_DIR/backend/requirements.txt"

# Generate secrets
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)
HOOK_SECRET=$(openssl rand -hex 16)

cat > "$REPO_DIR/backend/.env" <<ENV
SECRET_KEY=$SECRET_KEY
JWT_SECRET_KEY=$JWT_SECRET
FLASK_ENV=production
DATABASE_URL=postgresql://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME
GIT_REPOS_BASE=$GIT_BASE
GIT_USER=git
AUTHORIZED_KEYS_PATH=/home/git/.ssh/authorized_keys
INTERNAL_HOOK_SECRET=$HOOK_SECRET
INTERNAL_DOMAIN=securegit.local
BACKUP_DEST_PATH=/mnt/backup
ENV

chmod 600 "$REPO_DIR/backend/.env"

# Run migrations
cd "$REPO_DIR/backend"
FLASK_ENV=production "$VENV_DIR/bin/flask" db upgrade

# Run schema (idempotent)
sudo -u postgres psql -d "$DB_NAME" -f "$(dirname "$0")/../../database/schema.sql" || true

echo "Flask backend deployed and migrated."

# ---------------------------------------------------------------------------
# 6. Build React frontend
# ---------------------------------------------------------------------------
mkdir -p "$WWW_DIR"
cd "$(dirname "$0")/../../securegit-frontend"
npm ci --silent
npm run build
cp -r dist/. "$WWW_DIR/dist/"
chown -R www-data:www-data "$WWW_DIR"
echo "React frontend built and deployed to $WWW_DIR/dist."

# ---------------------------------------------------------------------------
# 7. Install Nginx config
# ---------------------------------------------------------------------------
cp "$(dirname "$0")/../nginx/securegit.conf" /etc/nginx/sites-available/securegit
ln -sf /etc/nginx/sites-available/securegit /etc/nginx/sites-enabled/securegit
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl enable nginx
systemctl restart nginx
echo "Nginx configured."

# ---------------------------------------------------------------------------
# 8. Install systemd service
# ---------------------------------------------------------------------------
mkdir -p "$LOG_DIR"
chown www-data:www-data "$LOG_DIR"
cp "$(dirname "$0")/../systemd/securegit-flask.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable securegit-flask
systemctl start securegit-flask
echo "Flask systemd service installed and started."

# ---------------------------------------------------------------------------
# 9. Configure dnsmasq
# ---------------------------------------------------------------------------
cp "$(dirname "$0")/../dns/dnsmasq.conf" /etc/dnsmasq.d/securegit.conf
sed -i "s/192.168.1.100/$SERVER_IP/g" /etc/dnsmasq.d/securegit.conf
systemctl enable dnsmasq
systemctl restart dnsmasq
echo "dnsmasq configured for securegit.local -> $SERVER_IP."

# ---------------------------------------------------------------------------
# 10. Configure UFW
# ---------------------------------------------------------------------------
bash "$(dirname "$0")/../ufw/setup.sh"

# ---------------------------------------------------------------------------
# 11. Generate SSL certificate
# ---------------------------------------------------------------------------
bash "$(dirname "$0")/setup-ssl.sh" "$SERVER_IP"

# ---------------------------------------------------------------------------
# 12. SSH configuration
# ---------------------------------------------------------------------------
cat "$(dirname "$0")/../ssh/sshd_config.additions" >> /etc/ssh/sshd_config
sshd -t && systemctl restart sshd
echo "SSH hardened."

# ---------------------------------------------------------------------------
# 13. Install post-receive hook template
# ---------------------------------------------------------------------------
cp "$(dirname "$0")/post-receive.sh" /usr/local/bin/securegit-post-receive
chmod +x /usr/local/bin/securegit-post-receive
sed -i "s/__HOOK_SECRET__/$HOOK_SECRET/g" /usr/local/bin/securegit-post-receive

# ---------------------------------------------------------------------------
# 14. Create initial admin user
# ---------------------------------------------------------------------------
cd "$REPO_DIR/backend"
"$VENV_DIR/bin/python" -c "
from app import create_app
from app.extensions import db, bcrypt
from app.models.user import User
import os
app = create_app('production')
with app.app_context():
    if not User.query.filter_by(username='admin').first():
        u = User(
            username='admin',
            email='admin@securegit.local',
            password_hash=bcrypt.generate_password_hash('$ADMIN_PASSWORD').decode('utf-8'),
            role='admin'
        )
        db.session.add(u)
        db.session.commit()
        print('Admin user created: admin / $ADMIN_PASSWORD')
    else:
        print('Admin user already exists.')
"

# ---------------------------------------------------------------------------
echo ""
echo "=============================="
echo " SecureGit setup complete!"
echo "=============================="
echo " Web UI:  https://securegit.local"
echo " SSH/Git: git@securegit.local"
echo " Admin:   admin / $ADMIN_PASSWORD"
echo " DB pass saved in: $REPO_DIR/backend/.env"
echo ""
echo " Point developer machines to $SERVER_IP as DNS server."
echo " Distribute /etc/ssl/securegit/fullchain.pem as trusted CA."
echo "=============================="
