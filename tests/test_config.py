import unittest
from app.config import Settings


class TestConfig(unittest.TestCase):
    def test_settings_parsing(self):
        s = Settings(
            switchbot_mac="aa:bb:cc:dd:ee:ff",
            switchbot_password="1234",
            telegram_allowed_users_raw="111, 222, invalid, 333",
        )
        self.assertEqual(s.switchbot_mac, "AA:BB:CC:DD:EE:FF")
        self.assertEqual(s.switchbot_password, "1234")
        self.assertEqual(s.allowed_users, {111, 222, 333})

    def test_empty_allowed_users(self):
        s = Settings(telegram_allowed_users_raw="")
        self.assertEqual(s.allowed_users, set())


if __name__ == "__main__":
    unittest.main()
