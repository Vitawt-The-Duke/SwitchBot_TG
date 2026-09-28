import time
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class ActionRecord:
    id: int
    timestamp: str
    time_str: str
    action: str
    user_id: int | str
    user_name: str
    chat_id: int | str | None
    chat_title: str | None
    success: bool
    message: str


class ActionHistory:
    def __init__(self, max_size: int = 100):
        self._max_size = max_size
        self._records: deque[ActionRecord] = deque(maxlen=max_size)
        self._counter: int = 0
        self._start_time: float = time.time()

    @property
    def uptime_seconds(self) -> int:
        return int(time.time() - self._start_time)

    def record(
        self,
        action: str,
        user_id: int | str = "system",
        user_name: str = "System",
        chat_id: int | str | None = None,
        chat_title: str | None = None,
        success: bool = True,
        message: str = "",
    ) -> ActionRecord:
        self._counter += 1
        now_utc = datetime.now(timezone.utc)
        record = ActionRecord(
            id=self._counter,
            timestamp=now_utc.isoformat(),
            time_str=now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
            action=action,
            user_id=user_id,
            user_name=user_name,
            chat_id=chat_id,
            chat_title=chat_title,
            success=success,
            message=message,
        )
        self._records.appendleft(record)
        return record

    def get_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        return [asdict(r) for r in list(self._records)[:limit]]

    def get_stats(self) -> dict[str, Any]:
        records = list(self._records)
        total = len(records)
        successes = sum(1 for r in records if r.success)
        failures = total - successes
        last_action = records[0].time_str if records else None
        return {
            "total_actions": self._counter,
            "recorded_recent": total,
            "successes": successes,
            "failures": failures,
            "last_action_at": last_action,
            "uptime_seconds": self.uptime_seconds,
        }

    def format_telegram_history(self, limit: int = 8) -> str:
        records = list(self._records)[:limit]
        if not records:
            return "📭 <b>Гісторыя дзеянняў пустая</b>\n(Яшчэ не было зарэгістравана націсканняў ці каманд)"

        lines = [f"📜 <b>Апошнія {len(records)} дзеянняў:</b>\n"]
        for idx, r in enumerate(records, start=1):
            status_icon = "✅" if r.success else "❌"
            action_names = {
                "press": "🔘 Кароткі націск",
                "long_press": "⏱️ Доўгі націск",
                "on": "🟢 Уключэнне (ON)",
                "off": "🔴 Выключэнне (OFF)",
                "info": "🔋 Запыт статусу",
                "scheduler": "⏰ Аўта-расклад (press)",
            }
            action_display = action_names.get(r.action, f"⚡ {r.action}")
            user_part = f"<b>{r.user_name}</b> (<code>{r.user_id}</code>)"
            chat_part = f" у <i>{r.chat_title}</i>" if r.chat_title else ""
            lines.append(
                f"{idx}. {status_icon} {action_display} — {user_part}{chat_part}\n"
                f"   🕒 <code>{r.time_str}</code> | {r.message}"
            )
        return "\n\n".join(lines)


action_history = ActionHistory()
