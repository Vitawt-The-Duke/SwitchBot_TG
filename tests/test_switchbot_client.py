import unittest
import tempfile
import os
from unittest.mock import patch, AsyncMock, MagicMock
from app.switchbot_client import SwitchBotClient, FileLock


class TestSwitchBotClient(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_lock = tempfile.NamedTemporaryFile(delete=False)
        self.temp_lock.close()
        self.client = SwitchBotClient(
            mac="AA:BB:CC:DD:EE:FF",
            password="1234",
            lock_path=self.temp_lock.name,
        )

    def tearDown(self):
        if os.path.exists(self.temp_lock.name):
            try:
                os.remove(self.temp_lock.name)
            except OSError:
                pass

    async def test_file_lock_context_manager(self):
        lock = FileLock(self.temp_lock.name)
        async with lock:
            self.assertIsNotNone(lock._fd)
        self.assertIsNone(lock._fd)

    @patch("app.switchbot_client.BleakScanner.find_device_by_address", new_callable=AsyncMock)
    @patch("app.switchbot_client.Switchbot")
    async def test_press_success(self, mock_switchbot_cls, mock_find_device):
        mock_device = MagicMock()
        mock_find_device.return_value = mock_device
        mock_bot = MagicMock()
        mock_bot.press = AsyncMock(return_value=True)
        mock_switchbot_cls.return_value = mock_bot

        res = await self.client.press()
        self.assertTrue(res["success"])
        self.assertIn("Action 'press' executed successfully!", res["message"])
        mock_bot.press.assert_awaited_once()

    @patch("app.switchbot_client.BleakScanner.find_device_by_address", new_callable=AsyncMock)
    @patch("app.switchbot_client.Switchbot")
    async def test_long_press_success(self, mock_switchbot_cls, mock_find_device):
        mock_device = MagicMock()
        mock_find_device.return_value = mock_device
        mock_bot = MagicMock()
        mock_bot.set_long_press = AsyncMock(return_value=True)
        mock_bot.press = AsyncMock(return_value=True)
        mock_switchbot_cls.return_value = mock_bot

        res = await self.client.long_press(duration=5)
        self.assertTrue(res["success"])
        mock_bot.set_long_press.assert_awaited_once_with(5)
        mock_bot.press.assert_awaited_once()

    @patch("app.switchbot_client.BleakScanner.find_device_by_address", new_callable=AsyncMock)
    @patch("app.switchbot_client.Switchbot")
    async def test_turn_on_and_off(self, mock_switchbot_cls, mock_find_device):
        mock_device = MagicMock()
        mock_find_device.return_value = mock_device
        mock_bot = MagicMock()
        mock_bot.turn_on = AsyncMock(return_value=True)
        mock_bot.turn_off = AsyncMock(return_value=True)
        mock_switchbot_cls.return_value = mock_bot

        res_on = await self.client.turn_on()
        self.assertTrue(res_on["success"])
        mock_bot.turn_on.assert_awaited_once()

        res_off = await self.client.turn_off()
        self.assertTrue(res_off["success"])
        mock_bot.turn_off.assert_awaited_once()

    @patch("app.switchbot_client.BleakScanner.find_device_by_address", new_callable=AsyncMock)
    @patch("app.switchbot_client.Switchbot")
    async def test_get_info(self, mock_switchbot_cls, mock_find_device):
        mock_device = MagicMock()
        mock_find_device.return_value = mock_device
        mock_bot = MagicMock()
        mock_bot.get_basic_info = AsyncMock(return_value={"battery": 90, "firmware": "4.9"})
        mock_switchbot_cls.return_value = mock_bot

        res = await self.client.get_info()
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["battery"], 90)

    @patch("app.switchbot_client.BleakScanner.find_device_by_address", new_callable=AsyncMock)
    async def test_device_not_found(self, mock_find_device):
        mock_find_device.return_value = None
        res = await self.client.press()
        self.assertFalse(res["success"])
        self.assertIn("not found in BLE scan", res["message"])

    @patch("app.switchbot_client.BleakScanner.find_device_by_address", new_callable=AsyncMock)
    @patch("app.switchbot_client.Switchbot")
    async def test_ble_exception(self, mock_switchbot_cls, mock_find_device):
        mock_device = MagicMock()
        mock_find_device.return_value = mock_device
        mock_bot = MagicMock()
        mock_bot.press = AsyncMock(side_effect=RuntimeError("GATT connection failed"))
        mock_switchbot_cls.return_value = mock_bot

        res = await self.client.press()
        self.assertFalse(res["success"])
        self.assertIn("BLE execution error: GATT connection failed", res["message"])


if __name__ == "__main__":
    unittest.main()
