import asyncio
import logging
import random
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

from app.config import settings
from app.switchbot_client import bot_client
from app.history import action_history

logger = logging.getLogger("scheduler")


class RandomScheduler:
    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None
        self._enabled = settings.scheduler_enabled
        self._start_hour = settings.scheduler_start_hour
        self._end_hour = settings.scheduler_end_hour
        self._workdays_only = settings.scheduler_workdays_only
        self._min_interval = settings.scheduler_min_interval_sec
        self._max_interval = settings.scheduler_max_interval_sec
        self._action = settings.scheduler_action
        self._tz_str = settings.scheduler_timezone
        self._total_triggers = 0
        self._last_trigger_time: str | None = None
        self._next_interval: float | None = None

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    def get_current_time(self) -> datetime:
        if ZoneInfo:
            try:
                tz = ZoneInfo(self._tz_str)
                return datetime.now(tz)
            except Exception:
                pass
        return datetime.now()

    def is_in_schedule_window(self, dt: datetime | None = None) -> bool:
        now = dt or self.get_current_time()
        # Monday is 0, Sunday is 6
        if self._workdays_only and now.weekday() >= 5:
            return False
        return self._start_hour <= now.hour < self._end_hour

    def get_next_interval(self) -> float:
        val = random.uniform(self._min_interval, self._max_interval)
        self._next_interval = round(val, 2)
        return self._next_interval

    async def execute_scheduled_action(self) -> dict:
        logger.info("Executing scheduled SwitchBot action: %s", self._action)
        if self._action == "long_press":
            res = await bot_client.long_press(5)
        else:
            res = await bot_client.press()

        self._total_triggers += 1
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        self._last_trigger_time = now_str

        action_history.record(
            action="scheduler",
            user_id="scheduler",
            user_name="🤖 Scheduler",
            success=res.get("success", False),
            message=f"Auto trigger ({self._action}): {res.get('message', '')}",
        )
        return res

    async def run(self):
        self._running = True
        logger.info(
            "Scheduler started (enabled=%s, window=%02d:00-%02d:00, workdays_only=%s, interval=%d-%ds, tz=%s)",
            self._enabled,
            self._start_hour,
            self._end_hour,
            self._workdays_only,
            self._min_interval,
            self._max_interval,
            self._tz_str,
        )

        while self._running:
            try:
                if not self._enabled:
                    await asyncio.sleep(10)
                    continue

                if not self.is_in_schedule_window():
                    # Check every 30 seconds if window has opened
                    await asyncio.sleep(30)
                    continue

                interval = self.get_next_interval()
                logger.info("Scheduler waiting %.1fs until next trigger...", interval)
                await asyncio.sleep(interval)

                # Re-verify window after sleep
                if self._running and self._enabled and self.is_in_schedule_window():
                    await self.execute_scheduled_action()

            except asyncio.CancelledError:
                logger.info("Scheduler task cancelled.")
                break
            except Exception as e:
                logger.warning("Scheduler error (retrying in 10s): %s", e)
                await asyncio.sleep(10)

        self._running = False

    def start_task(self) -> asyncio.Task:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run())
        return self._task

    def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()

    def get_status(self) -> dict:
        now = self.get_current_time()
        in_window = self.is_in_schedule_window(now)
        return {
            "enabled": self._enabled,
            "running": self._running,
            "in_schedule_window": in_window,
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S (%Z)"),
            "schedule_window": f"{self._start_hour:02d}:00 - {self._end_hour:02d}:00",
            "workdays_only": self._workdays_only,
            "min_interval_sec": self._min_interval,
            "max_interval_sec": self._max_interval,
            "next_interval_sec": self._next_interval,
            "total_triggers": self._total_triggers,
            "last_trigger_time": self._last_trigger_time,
            "timezone": self._tz_str,
            "action": self._action,
        }

    def format_telegram_status(self) -> str:
        st = self.get_status()
        state_icon = "🟢 Актыўны" if (st["enabled"] and st["in_schedule_window"]) else ("🟡 Чакае акна" if st["enabled"] else "🔴 Адключаны")
        workdays_str = "Панядзелак — Пятніца (Будні)" if st["workdays_only"] else "Кожны дзень"
        min_m = st["min_interval_sec"]
        max_m = st["max_interval_sec"]

        return (
            f"⏰ <b>Стан аўтаматычнага раскладу (Scheduler):</b>\n\n"
            f"• <b>Статус:</b> {state_icon}\n"
            f"• <b>Уключаны ў наладах:</b> {'Так' if st['enabled'] else 'Не'}\n"
            f"• <b>Часавае акно:</b> <code>{st['schedule_window']}</code> ({st['timezone']})\n"
            f"• <b>Дні:</b> {workdays_str}\n"
            f"• <b>Інтэрвал рандому:</b> ад {min_m}с да {max_m}с (~{max_m // 60} хв)\n"
            f"• <b>Цяперашні час:</b> <code>{st['current_time']}</code>\n"
            f"• <b>Усяго націсканняў:</b> <b>{st['total_triggers']}</b>\n"
            f"• <b>Апошняе націсканне:</b> <code>{st['last_trigger_time'] or 'яшчэ не было'}</code>"
        )


scheduler = RandomScheduler()
