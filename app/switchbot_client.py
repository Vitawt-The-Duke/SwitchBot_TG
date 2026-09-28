import asyncio
import logging
from typing import Any
from bleak import BleakScanner
from switchbot import Switchbot
from app.config import settings

logger = logging.getLogger("switchbot_client")


class SwitchBotClient:
    def __init__(self, mac: str | None = None, password: str | None = None):
        self.mac = (mac or settings.switchbot_mac).upper()
        self.password = password if password is not None else settings.switchbot_password
        self._lock = asyncio.Lock()

    async def _execute_action(self, action_name: str) -> dict[str, Any]:
        async with self._lock:
            logger.info("Scanning for SwitchBot %s...", self.mac)
            device = await BleakScanner.find_device_by_address(self.mac, timeout=10.0)
            if not device:
                msg = f"Device {self.mac} not found in BLE scan. Ensure phone app is closed and device is nearby."
                logger.warning(msg)
                return {"success": False, "message": msg, "data": None}

            logger.info("Connected to %s (%s). Executing %s...", device.address, device.name, action_name)
            bot = Switchbot(device, password=self.password)

            try:
                if action_name == "press":
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
                    return {"success": True, "message": f"Action \x27{action_name}\x27 executed successfully!", "data": None}
                else:
                    return {"success": False, "message": f"Action \x27{action_name}\x27 returned unsuccessful (check PIN/password).", "data": None}
            except Exception as e:
                logger.exception("Error during SwitchBot execution:")
                return {"success": False, "message": f"BLE execution error: {str(e)}", "data": None}

    async def press(self) -> dict[str, Any]:
        return await self._execute_action("press")

    async def turn_on(self) -> dict[str, Any]:
        return await self._execute_action("on")

    async def turn_off(self) -> dict[str, Any]:
        return await self._execute_action("off")

    async def get_info(self) -> dict[str, Any]:
        return await self._execute_action("info")


bot_client = SwitchBotClient()
