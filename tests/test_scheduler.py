import unittest
from datetime import datetime
from unittest.mock import patch, AsyncMock
from app.scheduler import RandomScheduler


class TestScheduler(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.scheduler = RandomScheduler()
        self.scheduler._start_hour = 9
        self.scheduler._end_hour = 17
        self.scheduler._workdays_only = True
        self.scheduler._min_interval = 1
        self.scheduler._max_interval = 420

    def test_schedule_window_workday(self):
        # 2026-09-28 is a Monday (weekday=0)
        dt_in_window = datetime(2026, 9, 28, 12, 0, 0)
        self.assertTrue(self.scheduler.is_in_schedule_window(dt_in_window))

        # Too early (8 AM)
        dt_early = datetime(2026, 9, 28, 8, 59, 59)
        self.assertFalse(self.scheduler.is_in_schedule_window(dt_early))

        # Too late (17 PM)
        dt_late = datetime(2026, 9, 28, 17, 0, 0)
        self.assertFalse(self.scheduler.is_in_schedule_window(dt_late))

    def test_schedule_window_weekend(self):
        # 2026-10-03 is Saturday (weekday=5)
        dt_saturday = datetime(2026, 10, 3, 12, 0, 0)
        self.assertFalse(self.scheduler.is_in_schedule_window(dt_saturday))

        # If workdays_only is False, weekend should be allowed
        self.scheduler._workdays_only = False
        self.assertTrue(self.scheduler.is_in_schedule_window(dt_saturday))

    def test_next_interval_range(self):
        for _ in range(20):
            interval = self.scheduler.get_next_interval()
            self.assertGreaterEqual(interval, 1.0)
            self.assertLessEqual(interval, 420.0)

    @patch("app.scheduler.bot_client.press", new_callable=AsyncMock)
    async def test_execute_scheduled_action(self, mock_press):
        mock_press.return_value = {"success": True, "message": "Action press executed successfully!"}
        res = await self.scheduler.execute_scheduled_action()
        self.assertTrue(res["success"])
        mock_press.assert_awaited_once()
        self.assertEqual(self.scheduler._total_triggers, 1)
        self.assertIsNotNone(self.scheduler._last_trigger_time)

    def test_enable_disable(self):
        self.scheduler.enable()
        self.assertTrue(self.scheduler.is_enabled)
        self.scheduler.disable()
        self.assertFalse(self.scheduler.is_enabled)

    def test_format_telegram_status(self):
        status_text = self.scheduler.format_telegram_status()
        self.assertIn("Стан аўтаматычнага раскладу", status_text)
        self.assertIn("09:00 - 17:00", status_text)


if __name__ == "__main__":
    unittest.main()
