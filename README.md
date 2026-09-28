# SwitchBot Gateway: Web Dashboard & Telegram Bot for Raspberry Pi

A lightweight, robust gateway to control **SwitchBot Bot (S1 / WoHand)** devices over Bluetooth Low Energy (BLE) with both a **Web Dashboard** and a **Telegram Bot**, designed specifically for Raspberry Pi (Pi 4 / Pi 5).

---

## 🌟 Features

- **🔘 1-Tap Control:** Press, Turn On, Turn Off, and Battery Status.
- **📱 Responsive Mobile Web UI:** Clean dark-mode dashboard running on FastAPI.
- **✈️ Telegram Bot:** Control from anywhere in the world with inline & reply keyboards.
- **🔒 Access Control:** Whitelist specific Telegram user IDs to prevent unauthorized triggers.
- **🛡️ BLE Concurrency Protection:** Built-in async mutex lock prevents BLE adapter collisions.
- **⚙️ Raspberry Pi 5 / Debian Trixie Ready:** Solves Linux BLE timeouts and PEP 668 constraints.

---

## 🚨 Critical Pi / BLE Gotchas & How We Solved Them

If setting this up on a fresh Raspberry Pi, be aware of these four critical pitfalls:

### 1. Package Name on PyPI is `PySwitchbot` (NOT `switchbot`)
- Running `pip install switchbot` fails with `No matching distribution found`.
- The official community library is **`PySwitchbot`**:
  ```bash
  pip install PySwitchbot
  ```

### 2. PEP 668 Externally Managed Environment
- Modern Raspberry Pi OS (Debian 12 Bookworm / Debian 13 Trixie, Python 3.11+) blocks `--break-system-packages`.
- **Solution:** Always use a dedicated virtual environment:
  ```bash
  python3 -m venv ~/switchbot-env
  source ~/switchbot-env/bin/activate
  pip install -r requirements.txt
  ```

### 3. The BLE Single-Connection Rule
- **SwitchBot Bot (S1) supports only ONE active BLE connection at a time.**
- If the official SwitchBot mobile app is open on your phone, your phone locks the BLE connection. The Pi will fail to connect with `TimeoutError` or `Device not found`.
- **Solution:** Force-close the SwitchBot app on your phone (or temporarily toggle Bluetooth off) before letting the Pi connect. Once the Pi gateway is running, use Telegram or the Web UI from your phone instead of the native app.

### 4. Linux Kernel BLE Supervision Timeout (`le-connection-abort-by-local`)
- By default in the Linux kernel on Raspberry Pi, the BLE supervision timeout is set to `42` (420 ms).
- SwitchBot devices take longer to respond to feature negotiation packets (`LL_FEATURE_REQ`), causing BlueZ to immediately drop the connection with `Connection Timeout (0x08)` and `le-connection-abort-by-local`.
- **Solution:** Increase the kernel BLE supervision timeout to `300` (3000 ms = 3.0 seconds):
  ```bash
  echo 300 | sudo tee /sys/kernel/debug/bluetooth/hci0/supervision_timeout
  ```
- This repository includes a systemd oneshot service (`switchbot-tune.service`) to keep this setting active across reboots.

---

## 🚀 Quick Setup on a New Raspberry Pi

### Step 1: Install System Dependencies
```bash
sudo apt update
sudo apt install -y bluetooth bluez rfkill python3-venv python3-pip git
```

### Step 2: Unblock and Verify Bluetooth
```bash
sudo rfkill unblock bluetooth
sudo systemctl restart bluetooth
sudo hciconfig hci0 up
```

### Step 3: Clone Repository and Setup Virtual Environment
```bash
git clone git@github.com:Vitawt-The-Duke/SwitchBot_TG.git /projects/SwitchBot_TG
cd /projects/SwitchBot_TG

python3 -m venv ~/switchbot-env
~/switchbot-env/bin/pip install --upgrade pip
~/switchbot-env/bin/pip install -r requirements.txt
```

### Step 4: Configure `.env`
```bash
cp .env.example .env
nano .env
```
Example `.env`:
```ini
# MAC address of your SwitchBot Bot (find in app: Settings -> Device Info -> BLE MAC)
SWITCHBOT_MAC=AA:BB:CC:DD:EE:FF

# Password / PIN if set in the SwitchBot app (leave empty if none)
SWITCHBOT_PASSWORD=your_password_here

# Telegram Bot Token from @BotFather (optional, leave empty if Web UI only)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxyz

# Comma-separated list of allowed Telegram user IDs (e.g. 123456789, 987654321)
TELEGRAM_ALLOWED_USER_IDS=123456789,987654321

# Optional: comma-separated allowed group/channel chat IDs (e.g. -1001234567890)
# Group administrators in these chats automatically get control access!
TELEGRAM_ALLOWED_CHAT_IDS=

# Web Server settings
WEB_HOST=0.0.0.0
WEB_PORT=8085

# Inter-process BLE Lock file
BLE_LOCK_FILE=/tmp/switchbot_ble.lock

# Random Workday Scheduler (Auto-presser)
SCHEDULER_ENABLED=false
SCHEDULER_START_HOUR=9
SCHEDULER_END_HOUR=17
SCHEDULER_WORKDAYS_ONLY=true
SCHEDULER_MIN_INTERVAL_SEC=1
SCHEDULER_MAX_INTERVAL_SEC=420
SCHEDULER_ACTION=press
SCHEDULER_TIMEZONE=Europe/Warsaw
```

### Step 5: Test via Command Line

You can run each component independently or together:

- **Run Web Dashboard & REST API separately:**
  ```bash
  ~/switchbot-env/bin/python3 -m app.web
  ```

- **Run Telegram Bot separately:**
  ```bash
  ~/switchbot-env/bin/python3 -m app.bot
  ```

- **Run Combined Gateway (Web + Telegram):**
  ```bash
  ~/switchbot-env/bin/python3 -m app.main
  ```

### Step 6: Install as Systemd Services (Auto-start on Boot)
```bash
chmod +x scripts/*.sh
./scripts/install_service.sh
```

This installs and starts independent services:
- `switchbot-web.service` (Web dashboard & REST API)
- `switchbot-bot.service` (Telegram Bot daemon)
- `switchbot-tune.service` (BLE kernel parameter tuning)

Inspect service logs individually:
```bash
# Web UI logs
sudo journalctl -u switchbot-web.service -f

# Telegram Bot logs
sudo journalctl -u switchbot-bot.service -f
```

---

## ✈️ Telegram Bot Commands & Channel Polling

The bot supports both private chats and group/channel chats:
- **Group/Channel Admin Authorization**: If the bot is added to a group or channel, all chat administrators automatically have permission to trigger actions and view diagnostics.
- **Whitelist Security**: Direct control restricted to `TELEGRAM_ALLOWED_USER_IDS` or chat admins.

### Bot Commands:
- `/press`: 🔘 Short momentary press (0s)
- `/longpress [sec]`: ⏱️ Long press (holds arm down for specified seconds, default 5s)
- `/on`: 🟢 Turn device switch ON
- `/off`: 🔴 Turn device switch OFF
- `/info`: 🔋 Battery percentage, firmware and mode
- `/health`: ❤️ Gateway health, uptime, lock state, and action counters
- `/history`: 📜 Action audit log showing the last actions and which user triggered them
- `/schedule`: ⏰ Workday random scheduler status and countdown
- `/help`: ❓ Full commands overview and interactive buttons

---

## 🌐 Web Dashboard & REST API

Open your browser at `http://<raspberry-pi-ip>:8085`.

### API Endpoints:
- `POST /api/press`: Triggers short press.
- `POST /api/longpress?duration=5`: Triggers long press with hold duration.
- `POST /api/on`: Triggers switch ON.
- `POST /api/off`: Triggers switch OFF.
- `GET /api/info`: Returns battery % and firmware info.
- `GET /api/health`: Health diagnostics and scheduler status.
- `GET /api/history`: Audit log of recent actions.
- `GET /api/schedule`: Workday scheduler status.

---

## 🧪 Running Tests
```bash
cd /projects/SwitchBot_TG
~/switchbot-env/bin/python3 -m unittest discover tests
```

---

## 📜 License
MIT License.
