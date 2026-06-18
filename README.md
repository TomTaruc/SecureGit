# SecureGit

A fully functional, self-hosted Git version control web platform equivalent in features to GitHub. Built for deployment on **Ubuntu Server 26.04 LTS** within a local Wi-Fi LAN.

**Stack:** React (Vite) + Flask (Python) + PostgreSQL  
**Design:** Strict monochrome — black / white / gray

---

## Architecture

```
[Developer Laptops] ──Wi-Fi──► [Router/AP] ──LAN──► [Ubuntu Server 26.04 LTS]
                                                           │
                         ┌─────────────────────────────────┤
                         │  Layer 1: UFW (ports 22, 443)   │
                         │  Layer 2: OpenSSH + chroot      │
                         │  Layer 3: Flask + Nginx          │
                         │  Layer 4: PostgreSQL             │
                         │  Layer 5: dnsmasq (DNS)         │
                         └─────────────────────────────────┘
```

## Project Layout

```
SecureGit/
├── securegit-backend/       # Flask application (Python)
├── securegit-frontend/      # React application (Vite)
├── infrastructure/          # Ubuntu server configuration files
│   ├── nginx/               # Nginx virtual host config
│   ├── ssh/                 # sshd_config additions
│   ├── ufw/                 # UFW firewall setup
│   ├── systemd/             # systemd service units
│   ├── dns/                 # dnsmasq internal DNS
│   └── scripts/             # Automated setup scripts
└── database/                # Reference SQL schema
```

## Quick Start (Development)

### Backend
```bash
cd securegit-backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # Edit with your DB credentials
flask db upgrade
python run.py
```

### Frontend
```bash
cd securegit-frontend
npm install
npm run dev
```

## Server Deployment

```bash
# On Ubuntu Server 26.04 LTS
sudo bash infrastructure/scripts/setup-server.sh
```

The setup script:
1. Installs all dependencies (git, postgresql, nginx, dnsmasq, python3, nodejs)
2. Creates the `git` system user + chroot jail base
3. Initializes PostgreSQL + `securegit_db`
4. Runs Flask-Migrate migrations
5. Builds the React frontend
6. Installs Nginx + systemd configs
7. Configures UFW rules
8. Generates self-signed SSL certificate

## Security Features

- **UFW Firewall** — only ports 22 (SSH) and 443 (HTTPS) open
- **Chroot Jails** — each user's SSH session sandboxed to `/srv/git/{username}/`
- **JWT Authentication** — short-lived (15min) access tokens + 7-day refresh tokens in `httpOnly` cookies
- **bcrypt** — password hashing at cost factor 12
- **RBAC** — 7 granular permissions per collaborator (read, push, create_branch, delete_branch, manage_collaborators, manage_settings, admin)
- **Branch Protection** — force-push prevention, delete protection, role-gated modifications
- **Rate Limiting** — login: 5/min, SSH key add: 10/hr
- **Audit Log** — immutable trail of all actions (actor, IP, timestamp)
- **PostgreSQL least-privilege** — dedicated `securegit_app` role, no DDL access

## Enhancement Features

- **Advanced RBAC** — granular `JSONB` permission flags per collaborator
- **Branch Protection Rules** — per-branch policies enforced at push time
- **Merge Management** — FF/squash/rebase merges, conflict detection, divergence analysis
- **Repository Tokens** — scoped machine tokens for CI/automated access
- **Automated Backups** — scheduled `pg_dump` + bare repo tar archives
- **Audit Log Streaming** — SSE endpoint for real-time admin feed
- **System Metrics** — CPU/RAM/disk via `psutil`, git object stats
- **Config Manager** — admin-editable instance settings
- **Internal Webhooks** — post-receive event dispatch to local services

## Access

- **Web UI:** `https://securegit.local`
- **SSH/Git:** `git@securegit.local`
- **DNS:** Point developer machines to server IP as DNS resolver

## License

Private — Unauthorized access is prohibited.
