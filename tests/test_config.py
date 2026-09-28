import unittest
from app.config import (
    Settings,
    parse_allowed_user_ids,
    parse_allowed_chat_ids,
    env_bool,
    env_int,
)


class TestConfig(unittest.TestCase):
    def test_parse_allowed_user_ids(self):
        # BaseLinker bot style parsing: ignore non-numeric, 0, and negative numbers
        res = parse_allowed_user_ids("111, 222, invalid, -5, 0, 333,  444 ")
        self.assertEqual(res, {111, 222, 333, 444})

        self.assertEqual(parse_allowed_user_ids(""), set())
        self.assertEqual(parse_allowed_user_ids(None), set())

    def test_parse_allowed_chat_ids(self):
        # Supports negative group IDs
        res = parse_allowed_chat_ids("-1001234567890, 999888, invalid")
        self.assertEqual(res, {-1001234567890, 999888})
        self.assertEqual(parse_allowed_chat_ids(""), set())

    def test_env_helpers(self):
        self.assertTrue(env_bool("NON_EXISTENT_KEY", True))
        self.assertFalse(env_bool("NON_EXISTENT_KEY", False))
        self.assertEqual(env_int("NON_EXISTENT_KEY", 42), 42)

    def test_settings_parsing_with_allowed_user_ids(self):
        s = Settings(
            switchbot_mac="aa:bb:cc:dd:ee:ff",
            switchbot_password="1234",
            telegram_allowed_user_ids_raw="111, 222, 333",
            telegram_allowed_chat_ids_raw="-1001234567890",
            scheduler_enabled=True,
            scheduler_start_hour=9,
            scheduler_end_hour=17,
        )
        self.assertEqual(s.switchbot_mac, "AA:BB:CC:DD:EE:FF")
        self.assertEqual(s.switchbot_password, "1234")
        self.assertEqual(s.allowed_users, {111, 222, 333})
        self.assertEqual(s.allowed_chats, {-1001234567890})
        self.assertTrue(s.scheduler_enabled)
        self.assertEqual(s.scheduler_start_hour, 9)
        self.assertEqual(s.scheduler_end_hour, 17)

    def test_empty_allowed_users(self):
        s = Settings(telegram_allowed_user_ids_raw="")
        self.assertEqual(s.allowed_users, set())
        self.assertEqual(s.ble_lock_file, "/tmp/switchbot_ble.lock")


if __name__ == "__main__":
    unittest.main()
