#!/bin/bash
set -euo pipefail

echo "=== Installing SwitchBot systemd services ==="
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

sudo cp "$PROJECT_DIR/systemd/switchbot-tune.service" /etc/systemd/system/
sudo cp "$PROJECT_DIR/systemd/switchbot-app.service" /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now switchbot-tune.service
sudo systemctl enable --now switchbot-app.service

echo "=== Status of switchbot-app.service ==="
sudo systemctl status switchbot-app.service --no-pager || true
