#!/bin/bash
# =============================================================================
# SecureGit SSL Certificate Generation (Self-Signed for LAN)
# Usage: sudo bash setup-ssl.sh [SERVER_IP]
# =============================================================================
set -euo pipefail

SERVER_IP="${1:-192.168.1.100}"
SSL_DIR="/etc/ssl/securegit"
CERT_DAYS=3650

mkdir -p "$SSL_DIR"

openssl req -x509 -nodes -days "$CERT_DAYS" -newkey rsa:4096 \
    -keyout "$SSL_DIR/privkey.pem" \
    -out    "$SSL_DIR/fullchain.pem" \
    -subj   "/C=PH/ST=Calabarzon/L=Local/O=SecureGit/CN=securegit.local" \
    -addext "subjectAltName=DNS:securegit.local,IP:$SERVER_IP"

chmod 600 "$SSL_DIR/privkey.pem"
chmod 644 "$SSL_DIR/fullchain.pem"

echo "SSL certificate generated at $SSL_DIR"
echo "Distribute fullchain.pem to developer machines as a trusted CA."
echo ""
echo "To trust on Ubuntu client:"
echo "  sudo cp fullchain.pem /usr/local/share/ca-certificates/securegit.crt"
echo "  sudo update-ca-certificates"
echo ""
echo "To trust on macOS client:"
echo "  sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain fullchain.pem"
