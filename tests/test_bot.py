import unittest
from unittest.mock import patch, AsyncMock, MagicMock
from aiogram import types
from app.config import settings
from app.bot import (
    is_user_allowed,
    get_reply_keyboard,
    get_inline_keyboard,
    start_handler,
    help_handler,
    execute_and_respond,
    callback_handler,
    run_bot,
    main,
)


class TestBot(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.original_allowed_users = settings.allowed_users
        self.original_token = settings.telegram_bot_token

    def tearDown(self):
        settings.allowed_users = self.original_allowed_users
        settings.telegram_bot_token = self.original_token

    def test_is_user_allowed_when_empty(self):
        settings.allowed_users = set()
        self.assertTrue(is_user_allowed(12345))

    def test_is_user_allowed_when_restricted(self):
        settings.allowed_users = {111, 222}
        self.assertTrue(is_user_allowed(111))
        self.assertFalse(is_user_allowed(999))

    def test_keyboards(self):
        reply_kb = get_reply_keyboard()
        self.assertIsNotNone(reply_kb.keyboard)
        button_texts = [btn.text for row in reply_kb.keyboard for btn in row]
        self.assertIn("🔘 Press", button_texts)
        self.assertIn("🟢 Turn ON", button_texts)
        self.assertIn("🔴 Turn OFF", button_texts)
        self.assertIn("🔋 Status & Battery", button_texts)

        inline_kb = get_inline_keyboard()
        cb_data = [btn.callback_data for row in inline_kb.inline_keyboard for btn in row]
        self.assertIn("press", cb_data)
        self.assertIn("on", cb_data)
        self.assertIn("off", cb_data)
        self.assertIn("info", cb_data)

    async def test_start_handler_allowed(self):
        settings.allowed_users = {123}
        msg = MagicMock(spec=types.Message)
        msg.from_user = MagicMock()
        msg.from_user.id = 123
        msg.answer = AsyncMock()
        await start_handler(msg)
        msg.answer.assert_awaited_once()
        self.assertIn("SwitchBot Controller Bot", msg.answer.await_args.args[0])

    async def test_start_handler_denied(self):
        settings.allowed_users = {123}
        msg = MagicMock(spec=types.Message)
        msg.from_user = MagicMock()
        msg.from_user.id = 999
        msg.answer = AsyncMock()
        await start_handler(msg)
        msg.answer.assert_awaited_once()
        self.assertIn("Access Denied", msg.answer.await_args.args[0])

    async def test_help_handler_allowed(self):
        settings.allowed_users = {123}
        msg = MagicMock(spec=types.Message)
        msg.from_user = MagicMock()
        msg.from_user.id = 123
        msg.answer = AsyncMock()
        await help_handler(msg)
        msg.answer.assert_awaited_once()
        self.assertIn("/press", msg.answer.await_args.args[0])

    async def test_help_handler_denied(self):
        settings.allowed_users = {123}
        msg = MagicMock(spec=types.Message)
        msg.from_user = MagicMock()
        msg.from_user.id = 999
        msg.answer = AsyncMock()
        await help_handler(msg)
        msg.answer.assert_not_awaited()

    @patch("app.bot.bot_client.press", new_callable=AsyncMock)
    async def test_execute_and_respond_press(self, mock_press):
        mock_press.return_value = {"success": True, "message": "Pressed!"}
        msg = MagicMock(spec=types.Message)
        status_msg = MagicMock()
        status_msg.edit_text = AsyncMock()
        msg.answer = AsyncMock(return_value=status_msg)

        await execute_and_respond(msg, "press")
        mock_press.assert_awaited_once()
        status_msg.edit_text.assert_awaited_once()
        self.assertIn("Pressed!", status_msg.edit_text.await_args.args[0])

    @patch("app.bot.bot_client.get_info", new_callable=AsyncMock)
    async def test_execute_and_respond_info(self, mock_info):
        mock_info.return_value = {
            "success": True,
            "message": "OK",
            "data": {"battery": 88, "firmware": "4.9", "switchMode": True},
        }
        msg = MagicMock(spec=types.Message)
        status_msg = MagicMock()
        status_msg.edit_text = AsyncMock()
        msg.answer = AsyncMock(return_value=status_msg)

        await execute_and_respond(msg, "info")
        mock_info.assert_awaited_once()
        status_msg.edit_text.assert_awaited_once()
        self.assertIn("88%", status_msg.edit_text.await_args.args[0])
        self.assertIn("Switch Mode", status_msg.edit_text.await_args.args[0])

    @patch("app.bot.bot_client.press", new_callable=AsyncMock)
    async def test_callback_handler_allowed(self, mock_press):
        settings.allowed_users = {123}
        mock_press.return_value = {"success": True, "message": "Pressed!"}
        callback = MagicMock(spec=types.CallbackQuery)
        callback.answer = AsyncMock()
        callback.from_user = MagicMock()
        callback.from_user.id = 123
        callback.data = "press"
        callback.message = MagicMock(spec=types.Message)
        status_msg = MagicMock()
        status_msg.edit_text = AsyncMock()
        callback.message.answer = AsyncMock(return_value=status_msg)

        await callback_handler(callback)
        callback.answer.assert_awaited_once()
        mock_press.assert_awaited_once()

    async def test_callback_handler_denied(self):
        settings.allowed_users = {123}
        callback = MagicMock(spec=types.CallbackQuery)
        callback.answer = AsyncMock()
        callback.from_user = MagicMock()
        callback.from_user.id = 999
        await callback_handler(callback)
        callback.answer.assert_awaited_once_with("Access Denied", show_alert=True)

    async def test_run_bot_no_token(self):
        settings.telegram_bot_token = None
        # Should exit gracefully without raising an exception
        await run_bot()

    @patch("app.bot.dp.start_polling", new_callable=AsyncMock)
    @patch("app.bot.Bot")
    async def test_run_bot_with_token(self, mock_bot_cls, mock_start_polling):
        settings.telegram_bot_token = "fake_token_123"
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
