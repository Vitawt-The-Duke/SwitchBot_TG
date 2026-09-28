import unittest
from unittest.mock import patch, AsyncMock, MagicMock
from aiogram import types
from app.config import settings
from app.bot import (
    is_user_authorized,
    get_reply_keyboard,
    get_inline_keyboard,
    start_handler,
    help_handler,
    execute_and_respond,
    msg_press,
    msg_long_press,
    msg_on,
    msg_off,
    msg_info,
    msg_health,
    msg_history,
    msg_schedule,
    callback_handler,
    run_bot,
    main,
)


def make_message(user_id=123, username="testuser", chat_id=123, chat_title=None, text=""):
    msg = MagicMock(spec=types.Message)
    msg.chat = MagicMock()
    msg.chat.id = chat_id
    msg.chat.title = chat_title
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.from_user.username = username
    msg.from_user.full_name = "Test User"
    msg.text = text
    status_msg = MagicMock()
    status_msg.edit_text = AsyncMock()
    msg.answer = AsyncMock(return_value=status_msg)
    return msg


def make_callback(user_id=123, username="testuser", chat_id=123, data="press"):
    cb = MagicMock(spec=types.CallbackQuery)
    cb.answer = AsyncMock()
    cb.data = data
    cb.from_user = MagicMock()
    cb.from_user.id = user_id
    cb.from_user.username = username
    cb.message = make_message(user_id=user_id, chat_id=chat_id)
    return cb


class TestBot(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.original_allowed_users = settings.allowed_users
        self.original_allowed_chats = settings.allowed_chats
        self.original_token = settings.telegram_bot_token
        self.original_scheduler_enabled = settings.scheduler_enabled
        self.mock_bot = MagicMock()

    def tearDown(self):
        settings.allowed_users = self.original_allowed_users
        settings.allowed_chats = self.original_allowed_chats
        settings.telegram_bot_token = self.original_token
        settings.scheduler_enabled = self.original_scheduler_enabled

    async def test_auth_open_when_empty(self):
        settings.allowed_users = set()
        settings.allowed_chats = set()
        self.assertTrue(await is_user_authorized(self.mock_bot, chat_id=123, user_id=456))

    async def test_auth_whitelist_user(self):
        settings.allowed_users = {111, 222}
        self.assertTrue(await is_user_authorized(self.mock_bot, chat_id=123, user_id=111))
        self.assertFalse(await is_user_authorized(self.mock_bot, chat_id=123, user_id=999))

    async def test_auth_group_admin(self):
        settings.allowed_users = {111}
        mock_member = MagicMock()
        mock_member.status = "administrator"
        self.mock_bot.get_chat_member = AsyncMock(return_value=mock_member)

        # User 999 is admin in group -10012345
        self.assertTrue(await is_user_authorized(self.mock_bot, chat_id=-10012345, user_id=999))
        self.mock_bot.get_chat_member.assert_awaited_once_with(chat_id=-10012345, user_id=999)

        # Regular member
        mock_member.status = "member"
        self.assertFalse(await is_user_authorized(self.mock_bot, chat_id=-10012345, user_id=999))

    async def test_auth_group_not_in_allowed_chats(self):
        settings.allowed_users = {111}
        settings.allowed_chats = {-1001111111111}
        self.assertFalse(await is_user_authorized(self.mock_bot, chat_id=-1009999999999, user_id=999))

    def test_keyboards(self):
        reply_kb = get_reply_keyboard()
        button_texts = [btn.text for row in reply_kb.keyboard for btn in row]
        self.assertIn("🔘 Short Press", button_texts)
        self.assertIn("⏱️ Long Press (5s)", button_texts)
        self.assertIn("🟢 Turn ON", button_texts)
        self.assertIn("🔴 Turn OFF", button_texts)
        self.assertIn("🔋 Battery & State", button_texts)
        self.assertIn("❤️ Health", button_texts)
        self.assertIn("📜 Action History", button_texts)
        self.assertIn("❓ Help", button_texts)

        inline_kb = get_inline_keyboard()
        cb_data = [btn.callback_data for row in inline_kb.inline_keyboard for btn in row]
        self.assertIn("press", cb_data)
        self.assertIn("long_press", cb_data)
        self.assertIn("on", cb_data)
        self.assertIn("off", cb_data)
        self.assertIn("info", cb_data)
        self.assertIn("health", cb_data)
        self.assertIn("history", cb_data)
        self.assertIn("schedule", cb_data)

    async def test_start_handler_allowed(self):
        settings.allowed_users = {123}
        msg = make_message(user_id=123, chat_id=123)
        await start_handler(msg, self.mock_bot)
        msg.answer.assert_awaited_once()
        self.assertIn("SwitchBot Gateway Controller", msg.answer.await_args.args[0])

    async def test_start_handler_denied(self):
        settings.allowed_users = {123}
        msg = make_message(user_id=999, chat_id=999)
        await start_handler(msg, self.mock_bot)
        msg.answer.assert_awaited_once()
        self.assertIn("Access Denied", msg.answer.await_args.args[0])

    async def test_help_handler(self):
        settings.allowed_users = {123}
        msg = make_message(user_id=123, chat_id=123)
        await help_handler(msg, self.mock_bot)
        msg.answer.assert_awaited_once()
        self.assertIn("/longpress", msg.answer.await_args.args[0])
        self.assertIn("/health", msg.answer.await_args.args[0])

    @patch("app.bot.bot_client.press", new_callable=AsyncMock)
    async def test_execute_and_respond_press(self, mock_press):
        mock_press.return_value = {"success": True, "message": "Pressed!"}
        msg = make_message(user_id=123, chat_id=123)
        status_msg = msg.answer.return_value

        await execute_and_respond(msg, "press")
        mock_press.assert_awaited_once_with(duration=0)
        status_msg.edit_text.assert_awaited_once()
        self.assertIn("Pressed!", status_msg.edit_text.await_args.args[0])

    @patch("app.bot.bot_client.long_press", new_callable=AsyncMock)
    async def test_execute_and_respond_long_press(self, mock_long_press):
        mock_long_press.return_value = {"success": True, "message": "Long pressed!"}
        msg = make_message(user_id=123, chat_id=123, chat_title="Test Group")
        status_msg = msg.answer.return_value

        await execute_and_respond(msg, "long_press", duration=10)
        mock_long_press.assert_awaited_once_with(duration=10)
        status_msg.edit_text.assert_awaited_once()
        self.assertIn("10 сек", status_msg.edit_text.await_args.args[0])

    @patch("app.bot.bot_client.long_press", new_callable=AsyncMock)
    async def test_msg_long_press_custom_arg(self, mock_long_press):
        settings.allowed_users = {123}
        mock_long_press.return_value = {"success": True, "message": "Done"}
        msg = make_message(user_id=123, chat_id=123, text="/longpress 8")

        await msg_long_press(msg, self.mock_bot)
        mock_long_press.assert_awaited_once_with(duration=8)

    async def test_msg_health_and_history_and_schedule(self):
        settings.allowed_users = {123}
        msg = make_message(user_id=123, chat_id=123)

        await msg_health(msg, self.mock_bot)
        msg.answer.assert_awaited_once()
        self.assertIn("Health", msg.answer.await_args.args[0])

        msg.answer.reset_mock()
        await msg_history(msg, self.mock_bot)
        msg.answer.assert_awaited_once()

        msg.answer.reset_mock()
        await msg_schedule(msg, self.mock_bot)
        msg.answer.assert_awaited_once()
        self.assertIn("Scheduler", msg.answer.await_args.args[0])

    @patch("app.bot.bot_client.press", new_callable=AsyncMock)
    async def test_callback_handler_allowed(self, mock_press):
        settings.allowed_users = {123}
        mock_press.return_value = {"success": True, "message": "Pressed!"}
        cb = make_callback(user_id=123, chat_id=123, data="press")

        await callback_handler(cb, self.mock_bot)
        cb.answer.assert_awaited_once()
        mock_press.assert_awaited_once()

    async def test_callback_handler_denied(self):
        settings.allowed_users = {123}
        cb = make_callback(user_id=999, chat_id=999, data="press")

        await callback_handler(cb, self.mock_bot)
        cb.answer.assert_awaited_once_with("⛔ Access Denied (Няма доступу)", show_alert=True)

    async def test_callback_handler_health_and_schedule(self):
        settings.allowed_users = {123}
        cb = make_callback(user_id=123, chat_id=123, data="health")

        await callback_handler(cb, self.mock_bot)
        cb.message.answer.assert_awaited_once()
        self.assertIn("Health", cb.message.answer.await_args.args[0])

        cb.message.answer.reset_mock()
        cb.data = "schedule"
        await callback_handler(cb, self.mock_bot)
        cb.message.answer.assert_awaited_once()
        self.assertIn("Scheduler", cb.message.answer.await_args.args[0])

    async def test_run_bot_no_token(self):
        settings.telegram_bot_token = None
        await run_bot()

    @patch("app.bot.dp.start_polling", new_callable=AsyncMock)
    @patch("app.bot.Bot")
    async def test_run_bot_with_token(self, mock_bot_cls, mock_start_polling):
        settings.telegram_bot_token = "fake_token_123"
        settings.scheduler_enabled = True
        mock_bot_instance = MagicMock()
        mock_bot_instance.session.close = AsyncMock()
        mock_bot_cls.return_value = mock_bot_instance

        await run_bot()
        mock_bot_cls.assert_called_once_with(token="fake_token_123")
        mock_start_polling.assert_awaited_once_with(mock_bot_instance)
        mock_bot_instance.session.close.assert_awaited_once()

    def test_main_without_token(self):
        settings.telegram_bot_token = None
        with patch("app.bot.asyncio.run") as mock_run:
            main()
            mock_run.assert_not_called()

    def test_main_with_token(self):
        settings.telegram_bot_token = "fake_token"
        with patch("app.bot.asyncio.run") as mock_run:
            main()
            mock_run.assert_called_once()
            coro = mock_run.call_args[0][0]
            coro.close()


if __name__ == "__main__":
    unittest.main()
