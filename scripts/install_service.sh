#!/bin/bash
set -euo pipefail

echo "=== Installing SwitchBot systemd services ==="
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Stop and disable legacy combined service if installed
if systemctl is-active --quiet switchbot-app.service 2>/dev/null; then
    echo "Stopping and disabling legacy switchbot-app.service..."
    sudo systemctl stop switchbot-app.service || true
    sudo systemctl disable switchbot-app.service || true
    sudo rm -f /etc/systemd/system/switchbot-app.service
fi

sudo cp "$PROJECT_DIR/systemd/switchbot-tune.service" /etc/systemd/system/
sudo cp "$PROJECT_DIR/systemd/switchbot-web.service" /etc/systemd/system/
sudo cp "$PROJECT_DIR/systemd/switchbot-bot.service" /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now switchbot-tune.service
sudo systemctl enable --now switchbot-web.service
sudo systemctl enable --now switchbot-bot.service

echo "=== Status of switchbot-web.service ==="
sudo systemctl status switchbot-web.service --no-pager || true

echo "=== Status of switchbot-bot.service ==="
sudo systemctl status switchbot-bot.service --no-pager || true
