#!/bin/bash
set -euo pipefail

echo "=== Tuning Bluetooth LE parameters for SwitchBot ==="
rfkill unblock bluetooth 2>/dev/null || true
hciconfig hci0 up 2>/dev/null || true

if [ -f /sys/kernel/debug/bluetooth/hci0/supervision_timeout ]; then
  echo 300 > /sys/kernel/debug/bluetooth/hci0/supervision_timeout
  echo "[OK] BLE supervision_timeout set to 300 (3000ms)"
else
  echo "[WARN] /sys/kernel/debug/bluetooth/hci0/supervision_timeout not found"
fi
