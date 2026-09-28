import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def parse_allowed_user_ids(raw: str | None) -> set[int]:
    """Parse comma-separated Telegram user IDs into a set of positive ints.
    Matches BaseLinker bot security pattern (ignores non-numeric, 0, or negative IDs).
    """
    if not raw:
        return set()
    result = set()
    for item in str(raw).split(","):
        clean = item.strip()
        if clean.isdigit():
            val = int(clean)
            if val > 0:
                result.add(val)
    return result


def parse_allowed_chat_ids(raw: str | None) -> set[int]:
    """Parse comma-separated Telegram chat IDs (allows negative IDs for groups/supergroups/channels)."""
    if not raw:
        return set()
    result = set()
    for item in str(raw).split(","):
        clean = item.strip()
        if clean.lstrip("-").isdigit():
            try:
                result.add(int(clean))
            except ValueError:
                pass
    return result


def env_bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("true", "1", "yes", "on")


def env_int(key: str, default: int) -> int:
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return int(val.strip())
    except ValueError:
        return default


@dataclass
class Settings:
    switchbot_mac: str = os.getenv("SWITCHBOT_MAC", "").strip()
    switchbot_password: str | None = os.getenv("SWITCHBOT_PASSWORD", "").strip() or None
    telegram_bot_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or None

    # Preferred: TELEGRAM_ALLOWED_USER_IDS, fallback to TELEGRAM_ALLOWED_USERS
    telegram_allowed_user_ids_raw: str = (
        os.getenv("TELEGRAM_ALLOWED_USER_IDS")
        or os.getenv("TELEGRAM_ALLOWED_USERS")
        or ""
    ).strip()

    # Allowed groups/channels where bot commands are honored (optional)
    telegram_allowed_chat_ids_raw: str = os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").strip()

    web_host: str = os.getenv("WEB_HOST", "0.0.0.0").strip()
    web_port: int = env_int("WEB_PORT", 8085)
    web_api_key: str | None = os.getenv("WEB_API_KEY", "").strip() or None
    ble_lock_file: str = os.getenv("BLE_LOCK_FILE", "/tmp/switchbot_ble.lock").strip()

    # Random Workday Scheduler Settings
    scheduler_enabled: bool = env_bool("SCHEDULER_ENABLED", False)
    scheduler_start_hour: int = env_int("SCHEDULER_START_HOUR", 9)
    scheduler_end_hour: int = env_int("SCHEDULER_END_HOUR", 17)
    scheduler_workdays_only: bool = env_bool("SCHEDULER_WORKDAYS_ONLY", True)
    scheduler_min_interval_sec: int = env_int("SCHEDULER_MIN_INTERVAL_SEC", 1)
    scheduler_max_interval_sec: int = env_int("SCHEDULER_MAX_INTERVAL_SEC", 420)  # 7 mins
    scheduler_action: str = os.getenv("SCHEDULER_ACTION", "press").strip()
    scheduler_timezone: str = os.getenv("SCHEDULER_TIMEZONE", "Europe/Warsaw").strip()

    allowed_users: set[int] = field(default_factory=set)
    allowed_chats: set[int] = field(default_factory=set)

    def __post_init__(self):
        self.switchbot_mac = self.switchbot_mac.upper()
        self.allowed_users = parse_allowed_user_ids(self.telegram_allowed_user_ids_raw)
        self.allowed_chats = parse_allowed_chat_ids(self.telegram_allowed_chat_ids_raw)


settings = Settings()
