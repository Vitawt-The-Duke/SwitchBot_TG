# SwitchBot_TG Developer & Agent Guidelines

## Architecture Overview

This project provides a unified Gateway service on Raspberry Pi 5 to control SwitchBot Bot (S1/WoHand) via Bluetooth Low Energy (BLE), offering both a REST/Web interface and Telegram Bot integration.

```
/projects/SwitchBot_TG/
├── app/
│   ├── config.py           # Configuration loader (dataclass from .env / env vars)
│   ├── switchbot_client.py # Async BLE client wrapping PySwitchbot with asyncio.Lock
│   ├── web.py              # FastAPI application + HTML endpoints
│   ├── bot.py              # Aiogram 3.x Telegram bot handlers & keyboards
│   ├── main.py             # Uvicorn + Aiogram async entrypoint runner
│   └── templates/
│       └── index.html      # Mobile-first dark-mode Web UI
├── tests/
│   ├── test_config.py      # Config parsing & allowed users tests
│   └── test_web.py         # FastAPI endpoint tests
├── scripts/
│   ├── tune_bluetooth.sh   # Sets BLE kernel parameters (supervision_timeout=3000ms)
│   └── install_service.sh  # Installs and enables systemd units
└── systemd/
    ├── switchbot-tune.service # Oneshot tuning service on boot
    └── switchbot-app.service  # Main daemon service
```

---

## Known Gotchas & Pitfalls

1. **PySwitchbot vs switchbot**:
   Always use `PySwitchbot` from PyPI. `pip install switchbot` does not exist.

2. **BLE Single Peripheral Connection**:
   SwitchBot S1 allows only 1 BLE central at a time. The mobile app MUST be closed or disconnected before testing from Linux.

3. **Linux Kernel Supervision Timeout**:
   Default `supervision_timeout` on Raspberry Pi 5 is 42 (420ms). It causes `le-connection-abort-by-local` and disconnects with `Connection Timeout (0x08)`. Must be set to `300` (3000ms) via debugfs:
   `/sys/kernel/debug/bluetooth/hci0/supervision_timeout`.

4. **BLE Locking**:
   Never invoke simultaneous BLE operations. `switchbot_client.py` uses `asyncio.Lock()` to serialize calls across web and telegram.

---

## Development & Testing Commands

- Run tests:
  ```bash
  ~/switchbot-env/bin/python3 -m unittest discover tests
  ```
- Run server manually:
  ```bash
  ~/switchbot-env/bin/python3 -m app.main
  ```
- Service management:
  ```bash
  sudo systemctl restart switchbot-app.service
  sudo journalctl -u switchbot-app.service -f
  ```
