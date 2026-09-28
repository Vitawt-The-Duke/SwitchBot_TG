import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    switchbot_mac: str = os.getenv("SWITCHBOT_MAC", "").strip()
    switchbot_password: str | None = os.getenv("SWITCHBOT_PASSWORD", "").strip() or None
    telegram_bot_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or None
    telegram_allowed_users_raw: str = os.getenv("TELEGRAM_ALLOWED_USERS", "").strip()
    web_host: str = os.getenv("WEB_HOST", "0.0.0.0").strip()
    web_port: int = int(os.getenv("WEB_PORT", "8085"))
    web_api_key: str | None = os.getenv("WEB_API_KEY", "").strip() or None
    ble_lock_file: str = os.getenv("BLE_LOCK_FILE", "/tmp/switchbot_ble.lock").strip()

    allowed_users: set[int] = field(default_factory=set)

    def __post_init__(self):
        self.switchbot_mac = self.switchbot_mac.upper()
        if self.telegram_allowed_users_raw:
            users = set()
            for part in self.telegram_allowed_users_raw.split(","):
                part = part.strip()
                if part.isdigit():
                    users.add(int(part))
            self.allowed_users = users


settings = Settings()
