import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from app.config import settings
from app.switchbot_client import bot_client

logger = logging.getLogger("telegram_bot")

dp = Dispatcher()


def is_user_allowed(user_id: int) -> bool:
    if not settings.allowed_users:
        return True
    return user_id in settings.allowed_users


def get_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔘 Press")],
            [KeyboardButton(text="🟢 Turn ON"), KeyboardButton(text="🔴 Turn OFF")],
            [KeyboardButton(text="🔋 Status & Battery")],
        ],
        resize_keyboard=True,
    )


def get_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔘 Press Bot", callback_data="press")],
            [
                InlineKeyboardButton(text="🟢 On", callback_data="on"),
                InlineKeyboardButton(text="🔴 Off", callback_data="off"),
            ],
            [InlineKeyboardButton(text="🔋 Status / Battery", callback_data="info")],
        ]
    )


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user_id = message.from_user.id if message.from_user else 0
    if not is_user_allowed(user_id):
        await message.answer(f"⛔ Access Denied. Your Telegram User ID: <code>{user_id}</code>", parse_mode="HTML")
        return

    text = (
        f"👋 <b>SwitchBot Controller Bot</b>\n\n"
        f"📍 <b>Device MAC:</b> <code>{settings.switchbot_mac}</code>\n"
        f"🎮 Choose an action using the buttons below:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_reply_keyboard())


@dp.message(Command("help"))
async def help_handler(message: types.Message):
    user_id = message.from_user.id if message.from_user else 0
    if not is_user_allowed(user_id):
        return
    text = (
        "Commands:\n"
        "/start - Show control keyboard\n"
        "/press - Execute Press\n"
        "/on - Turn On\n"
        "/off - Turn Off\n"
        "/info - Check battery and state"
    )
    await message.answer(text)


async def execute_and_respond(event: types.Message | types.CallbackQuery, action: str):
    msg_target = event if isinstance(event, types.Message) else event.message
    status_msg = await msg_target.answer(f"⏳ Communicating with SwitchBot ({action})...")

    if action == "press":
        res = await bot_client.press()
    elif action == "on":
        res = await bot_client.turn_on()
    elif action == "off":
        res = await bot_client.turn_off()
    elif action == "info":
        res = await bot_client.get_info()
    else:
        res = {"success": False, "message": f"Unknown action: {action}"}

    if res["success"]:
        if action == "info" and res.get("data"):
            d = res["data"]
            mode_str = "Switch Mode" if d.get("switchMode") else "Press Mode"
            text = (
                f"✅ <b>Device Status</b>\n"
                f"🔋 Battery: <b>{d.get('battery')}%</b>\n"
                f"⚙️ Firmware: {d.get('firmware')}\n"
                f"📌 Mode: {mode_str}"
            )
        else:
            text = f"✅ {res['message']}"
    else:
        text = f"❌ {res['message']}"

    await status_msg.edit_text(text, parse_mode="HTML")


@dp.message(F.text == "🔘 Press")
@dp.message(Command("press"))
async def msg_press(message: types.Message):
    if not is_user_allowed(message.from_user.id):
        return
    await execute_and_respond(message, "press")


@dp.message(F.text == "🟢 Turn ON")
@dp.message(Command("on"))
async def msg_on(message: types.Message):
    if not is_user_allowed(message.from_user.id):
        return
    await execute_and_respond(message, "on")


@dp.message(F.text == "🔴 Turn OFF")
@dp.message(Command("off"))
async def msg_off(message: types.Message):
    if not is_user_allowed(message.from_user.id):
        return
    await execute_and_respond(message, "off")


@dp.message(F.text == "🔋 Status & Battery")
@dp.message(Command("info"))
async def msg_info(message: types.Message):
    if not is_user_allowed(message.from_user.id):
        return
    await execute_and_respond(message, "info")


@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery):
    if not is_user_allowed(callback.from_user.id):
        await callback.answer("Access Denied", show_alert=True)
        return
    await callback.answer()
    if callback.data in ["press", "on", "off", "info"]:
        await execute_and_respond(callback, callback.data)


async def run_bot():
    if not settings.telegram_bot_token:
        logger.info("No TELEGRAM_BOT_TOKEN provided. Telegram bot will not start.")
        return
    bot = Bot(token=settings.telegram_bot_token)
    logger.info("Starting Telegram Bot long-polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
