#!/bin/bash
# =============================================================================
# SecureGit UFW Firewall Setup
# Run as root on Ubuntu Server 26.04 LTS
# =============================================================================
set -euo pipefail

echo "Configuring UFW firewall for SecureGit..."

# Reset to defaults
ufw --force reset

# Default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (Git operations + admin)
ufw allow 22/tcp comment 'SSH - Git operations and server admin'

# Allow HTTPS (Web UI)
ufw allow 443/tcp comment 'HTTPS - SecureGit Web UI'

# Explicitly deny plain HTTP (Nginx handles redirect internally)
ufw deny 80/tcp comment 'HTTP - deny; redirect handled by Nginx'

# Allow loopback
ufw allow in on lo
ufw allow out on lo

# Enable UFW
ufw --force enable
ufw status verbose

echo "UFW configured. Open ports: 22 (SSH), 443 (HTTPS)."
