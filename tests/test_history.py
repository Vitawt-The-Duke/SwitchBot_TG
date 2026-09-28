import unittest
from app.history import ActionHistory


class TestHistory(unittest.TestCase):
    def setUp(self):
        self.history = ActionHistory(max_size=5)

    def test_record_and_recent(self):
        r1 = self.history.record(action="press", user_id=123, user_name="User1", success=True, message="OK")
        r2 = self.history.record(action="on", user_id=456, user_name="User2", success=False, message="Fail")

        recent = self.history.get_recent(limit=10)
        self.assertEqual(len(recent), 2)
        # Most recent first
        self.assertEqual(recent[0]["action"], "on")
        self.assertEqual(recent[1]["action"], "press")

    def test_stats(self):
        self.history.record(action="press", success=True)
        self.history.record(action="off", success=True)
        self.history.record(action="info", success=False)

        stats = self.history.get_stats()
        self.assertEqual(stats["total_actions"], 3)
        self.assertEqual(stats["successes"], 2)
        self.assertEqual(stats["failures"], 1)
        self.assertGreaterEqual(stats["uptime_seconds"], 0)

    def test_format_telegram_history(self):
        empty_text = self.history.format_telegram_history()
        self.assertIn("пустая", empty_text)

        self.history.record(action="press", user_id=111, user_name="Alice", success=True, message="Success")
        text = self.history.format_telegram_history()
        self.assertIn("Alice", text)
        self.assertIn("Кароткі націск", text)
        self.assertIn("111", text)


if __name__ == "__main__":
    unittest.main()
