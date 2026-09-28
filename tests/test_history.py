import os
import gzip
import logging
import tempfile
import unittest
from app.history import ActionHistory
from app.logger import CompressedRotatingFileHandler


class TestHistory(unittest.TestCase):
    def setUp(self):
        self.history = ActionHistory(max_size=5, log_file="")

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

    def test_file_persistence_and_reload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "actions.log")
            h1 = ActionHistory(max_size=5, log_file=log_file)
            h1.record(action="press", user_id=101, user_name="Bob", success=True, message="OK")
            h1.record(action="long_press", user_id=102, user_name="Charlie", success=True, message="Done")

            # Verify file was written
            h1.close()
            self.assertTrue(os.path.exists(log_file))
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            self.assertEqual(len(lines), 2)

            # Reload into new instance
            h2 = ActionHistory(max_size=5, log_file=log_file)
            recent = h2.get_recent(limit=10)
            self.assertEqual(len(recent), 2)
            self.assertEqual(recent[0]["action"], "long_press")
            self.assertEqual(recent[1]["action"], "press")
            self.assertEqual(h2._counter, 2)
            h2.close()

    def test_compressed_rotating_handler(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            # Set maxBytes small to trigger rotation
            handler = CompressedRotatingFileHandler(log_file, maxBytes=200, backupCount=3)
            logger = logging.getLogger("test_rotator")
            logger.setLevel(logging.INFO)
            logger.addHandler(handler)

            # Write enough data to trigger multiple rotations
            for i in range(25):
                logger.info(f"Line number {i}: " + "X" * 30)

            handler.close()
            logger.removeHandler(handler)

            # Check that rotated .gz file was created
            rotated_gz = log_file + ".1.gz"
            self.assertTrue(os.path.exists(rotated_gz), f"Expected {rotated_gz} to exist")

            # Verify it is a valid gzip archive
            with gzip.open(rotated_gz, "rt", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("Line number", content)


if __name__ == "__main__":
    unittest.main()
