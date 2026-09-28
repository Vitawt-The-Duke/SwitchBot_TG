import asyncio
import logging
from typing import Any
from bleak import BleakScanner
from switchbot import Switchbot
from app.config import settings

try:
    import fcntl
except ImportError:
    fcntl = None

logger = logging.getLogger("switchbot_client")


class FileLock:
    def __init__(self, lock_path: str = "/tmp/switchbot_ble.lock"):
        self.lock_path = lock_path
        self._fd = None

    def acquire(self):
        if fcntl is None:
            return
        try:
            self._fd = open(self.lock_path, "w+")
            fcntl.flock(self._fd, fcntl.LOCK_EX)
        except Exception as e:
            logger.warning("Could not acquire file lock %s: %s", self.lock_path, e)

    def release(self):
        if fcntl is None or not self._fd:
            return
        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            self._fd.close()
        except Exception as e:
            logger.warning("Error releasing file lock %s: %s", self.lock_path, e)
        finally:
            self._fd = None

    async def __aenter__(self):
        await asyncio.to_thread(self.acquire)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await asyncio.to_thread(self.release)


class SwitchBotClient:
    def __init__(self, mac: str | None = None, password: str | None = None, lock_path: str | None = None):
        self.mac = (mac or settings.switchbot_mac).upper()
        self.password = password if password is not None else settings.switchbot_password
        self._lock = asyncio.Lock()
        self.file_lock = FileLock(lock_path or settings.ble_lock_file)

    async def _execute_action(self, action_name: str, **kwargs: Any) -> dict[str, Any]:
        async with self._lock:
            async with self.file_lock:
                logger.info("Scanning for SwitchBot %s...", self.mac)
                device = None
                for attempt in range(2):
                    device = await BleakScanner.find_device_by_address(self.mac, timeout=8.0)
                    if device:
                        break
                    if attempt == 0:
                        await asyncio.sleep(0.5)

                if not device:
                    msg = f"Device {self.mac} not found in BLE scan. Ensure phone app is closed and device is nearby."
                    logger.warning(msg)
                    return {"success": False, "message": msg, "data": None}

                logger.info("Connected to %s (%s). Executing %s...", device.address, device.name, action_name)
                bot = Switchbot(device, password=self.password)

                try:
                    if action_name == "press":
                        duration = kwargs.get("duration", 0)
                        if duration > 0:
                            try:
                                await bot.set_long_press(duration)
                            except Exception as e:
                                logger.debug("set_long_press error: %s", e)
                        res = await bot.press()
                    elif action_name == "long_press":
                        duration = kwargs.get("duration", 5)
                        try:
                            await bot.set_long_press(duration)
                        except Exception as e:
                            logger.warning("Failed setting long press duration: %s", e)
                        res = await bot.press()
                    elif action_name == "on":
                        res = await bot.turn_on()
                    elif action_name == "off":
                        res = await bot.turn_off()
                    elif action_name == "info":
                        info = await bot.get_basic_info()
                        return {
                            "success": True,
                            "message": "Device info retrieved successfully",
                            "data": info,
                        }
                    else:
                        return {"success": False, "message": f"Unknown action: {action_name}", "data": None}

                    if res:
                        return {"success": True, "message": f"Action '{action_name}' executed successfully!", "data": None}
                    else:
                        return {"success": False, "message": f"Action '{action_name}' returned unsuccessful (check PIN/password).", "data": None}
                except Exception as e:
                    logger.exception("Error during SwitchBot execution:")
                    return {"success": False, "message": f"BLE execution error: {str(e)}", "data": None}
                finally:
                    try:
                        disc = getattr(bot, "_execute_forced_disconnect", None)
                        if callable(disc):
                            res_disc = disc()
                            if asyncio.iscoroutine(res_disc):
                                await res_disc
                    except Exception as disc_err:
                        logger.debug("Disconnect cleanup error: %s", disc_err)
                    await asyncio.sleep(0.5)

    async def press(self, duration: int = 0) -> dict[str, Any]:
        """Short momentary press."""
        return await self._execute_action("press", duration=duration)

    async def long_press(self, duration: int = 5) -> dict[str, Any]:
        """Long press holding arm down for duration seconds (default 5s)."""
        return await self._execute_action("long_press", duration=duration)

    async def turn_on(self) -> dict[str, Any]:
        return await self._execute_action("on")

    async def turn_off(self) -> dict[str, Any]:
        return await self._execute_action("off")

    async def get_info(self) -> dict[str, Any]:
        return await self._execute_action("info")


bot_client = SwitchBotClient()
