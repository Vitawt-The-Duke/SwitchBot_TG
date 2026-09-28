# SwitchBot_TG Developer & Agent Guidelines

## Architecture Overview

This project provides a unified Gateway service on Raspberry Pi 5 to control SwitchBot Bot (S1/WoHand) via Bluetooth Low Energy (BLE), offering both a REST/Web interface and Telegram Bot integration.

```
/projects/SwitchBot_TG/
├── app/
│   ├── config.py           # Configuration loader (dataclass from .env / env vars)
│   ├── switchbot_client.py # Async BLE client wrapping PySwitchbot with asyncio.Lock & FileLock
│   ├── web.py              # FastAPI application + HTML endpoints (standalone runner via `python -m app.web`)
│   ├── bot.py              # Aiogram 3.x Telegram bot handlers (standalone runner via `python -m app.bot`)
│   ├── main.py             # Combined Uvicorn + Aiogram async runner
│   └── templates/
│       └── index.html      # Mobile-first dark-mode Web UI
├── tests/
│   ├── test_config.py           # Config parsing & allowed users tests
│   ├── test_web.py              # FastAPI endpoint tests
│   ├── test_bot.py              # Aiogram handlers & keyboards tests
│   └── test_switchbot_client.py # SwitchBotClient & FileLock tests
├── scripts/
│   ├── tune_bluetooth.sh   # Sets BLE kernel parameters (supervision_timeout=3000ms)
│   └── install_service.sh  # Installs and enables systemd units
└── systemd/
    ├── switchbot-tune.service # Oneshot tuning service on boot
    ├── switchbot-web.service  # Standalone Web Dashboard & REST API service
    └── switchbot-bot.service  # Standalone Telegram Bot service
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

4. **BLE Locking (Process & Thread Safety)**:
   Never invoke simultaneous BLE operations. `switchbot_client.py` uses `asyncio.Lock()` for intra-process serialization and an inter-process `FileLock` (`fcntl.flock` on `/tmp/switchbot_ble.lock`) to serialize calls across independent processes (e.g. `switchbot-web.service` and `switchbot-bot.service`).

---

## Development & Testing Commands

- Run tests:
  ```bash
  ~/switchbot-env/bin/python3 -m unittest discover tests
  ```
- Run web server separately:
  ```bash
  ~/switchbot-env/bin/python3 -m app.web
  ```
- Run telegram bot separately:
  ```bash
  ~/switchbot-env/bin/python3 -m app.bot
  ```
- Run combined gateway:
  ```bash
  ~/switchbot-env/bin/python3 -m app.main
  ```
- Service management:
  ```bash
  sudo systemctl restart switchbot-web.service switchbot-bot.service
  sudo journalctl -u switchbot-web.service -f
  sudo journalctl -u switchbot-bot.service -f
  ```
