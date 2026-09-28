import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from app.config import settings
from app.switchbot_client import bot_client
from app.history import action_history
from app.scheduler import scheduler

logger = logging.getLogger("telegram_bot")

dp = Dispatcher()


async def is_user_authorized(bot: Bot, chat_id: int, user_id: int, chat_type: str = "private") -> bool:
    logger.info(
        "Auth check: user_id=%s, chat_id=%s, chat_type=%s | allowed_users=%s, allowed_chats=%s",
        user_id, chat_id, chat_type, settings.allowed_users, settings.allowed_chats
    )
    if not settings.allowed_users and not settings.allowed_chats:
        return True

    if user_id and user_id in settings.allowed_users:
        return True

    # Channel authorization
    if chat_type == "channel" or (chat_id < 0 and user_id == 0):
        if settings.allowed_chats:
            return chat_id in settings.allowed_chats
        return True

    # Group / supergroup authorization
    if chat_id < 0:
        if settings.allowed_chats and chat_id not in settings.allowed_chats:
            return False
        if user_id > 0:
            try:
                member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
                if member.status in ("creator", "administrator"):
                    return True
            except Exception as e:
                logger.warning("Could not fetch chat member status for user %s in %s: %s", user_id, chat_id, e)

    return False


def get_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔘 Short Press"), KeyboardButton(text="⏱️ Long Press (5s)")],
            [KeyboardButton(text="🟢 Turn ON"), KeyboardButton(text="🔴 Turn OFF")],
            [KeyboardButton(text="🔋 Battery & State"), KeyboardButton(text="❤️ Health")],
            [KeyboardButton(text="📜 Action History"), KeyboardButton(text="❓ Help")],
        ],
        resize_keyboard=True,
    )


def get_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔘 Short Press", callback_data="press"),
                InlineKeyboardButton(text="⏱️ Long Press (5s)", callback_data="long_press"),
            ],
            [
                InlineKeyboardButton(text="🟢 Turn ON", callback_data="on"),
                InlineKeyboardButton(text="🔴 Turn OFF", callback_data="off"),
            ],
            [
                InlineKeyboardButton(text="🔋 Device Info", callback_data="info"),
                InlineKeyboardButton(text="❤️ Health", callback_data="health"),
            ],
            [
                InlineKeyboardButton(text="📜 Action History", callback_data="history"),
                InlineKeyboardButton(text="⏰ Scheduler", callback_data="schedule"),
            ],
        ]
    )


def get_user_display_name(event: types.Message | types.CallbackQuery) -> tuple[int | str, str]:
    user = event.from_user
    if user:
        name = f"@{user.username}" if user.username else (user.full_name or str(user.id))
        return user.id, name

    if isinstance(event, types.Message):
        if event.sender_chat and event.sender_chat.title:
            return f"channel_{event.chat.id}", f"📢 {event.sender_chat.title}"
        if event.chat and event.chat.title:
            return f"channel_{event.chat.id}", f"📢 {event.chat.title}"

    return "channel_admin", "📢 Channel Admin"


@dp.message(CommandStart())
@dp.channel_post(CommandStart())
async def start_handler(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    chat_type = message.chat.type or "private"

    if not await is_user_authorized(bot, chat_id, user_id, chat_type):
        await message.answer(
            f"⛔ <b>Access Denied</b>\nYour User ID: <code>{user_id}</code> | Chat ID: <code>{chat_id}</code>\n"
            f"To grant access, add User ID to <code>TELEGRAM_ALLOWED_USER_IDS</code> or Chat ID to <code>TELEGRAM_ALLOWED_CHAT_IDS</code> in <code>.env</code>.",
            parse_mode="HTML"
        )
        return

    text = (
        f"👋 <b>SwitchBot Gateway Controller</b>\n\n"
        f"📍 <b>Device MAC:</b> <code>{settings.switchbot_mac}</code>\n"
        f"🎮 Control your device using the buttons below or commands (/help):"
    )
    if chat_type == "channel":
        await message.answer(text, parse_mode="HTML", reply_markup=get_inline_keyboard())
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=get_reply_keyboard())


@dp.message(Command("help"))
@dp.channel_post(Command("help"))
@dp.message(F.text == "❓ Help")
async def help_handler(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    chat_type = message.chat.type or "private"
    logger.info("Received /help in chat_id=%s (%s, title=%r), from user_id=%s", chat_id, chat_type, message.chat.title, user_id)

    if not await is_user_authorized(bot, chat_id, user_id, chat_type):
        await message.answer(
            f"⛔ <b>Access Denied</b>\n"
            f"Chat ID: <code>{chat_id}</code> | User ID: <code>{user_id}</code>\n\n"
            f"To grant access to this chat/channel, add to <code>.env</code>:\n"
            f"<code>TELEGRAM_ALLOWED_CHAT_IDS={chat_id}</code>",
            parse_mode="HTML"
        )
        return

    text = (
        "🤖 <b>SwitchBot Bot Command Reference:</b>\n\n"
        "🔘 <b>Device Controls:</b>\n"
        "• <code>/press</code> — Short momentary press\n"
        "• <code>/longpress [sec]</code> — Long press holding arm down (default: 5s)\n"
        "• <code>/on</code> — Turn switch ON\n"
        "• <code>/off</code> — Turn switch OFF\n"
        "• <code>/info</code> — Query device status & battery\n\n"
        "📊 <b>Monitoring & Service:</b>\n"
        "• <code>/health</code> — Gateway health, service status & Bluetooth\n"
        "• <code>/history</code> — Action audit log (recent triggers)\n"
        "• <code>/schedule</code> — Workday scheduler status (or <code>/schedule on</code> / <code>/schedule off</code>)\n"
        "• <code>/help</code> — Show this command reference\n\n"
        "<i>Interactive controls via buttons below:</i>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_inline_keyboard())


async def execute_and_respond(event: types.Message | types.CallbackQuery, action: str, duration: int = 5):
    msg_target = event if isinstance(event, types.Message) else event.message
    status_msg = await msg_target.answer(f"⏳ Connecting to SwitchBot ({action})...")

    user_id, user_name = get_user_display_name(event)
    chat = event.chat if isinstance(event, types.Message) else (event.message.chat if event.message else None)
    chat_id = chat.id if chat else None
    chat_title = chat.title if chat else None

    if action == "press":
        res = await bot_client.press(duration=0)
    elif action == "long_press":
        res = await bot_client.long_press(duration=duration)
    elif action == "on":
        res = await bot_client.turn_on()
    elif action == "off":
        res = await bot_client.turn_off()
    elif action == "info":
        res = await bot_client.get_info()
    else:
        res = {"success": False, "message": f"Unknown action: {action}"}

    success = res.get("success", False)
    msg_text = res.get("message", "")

    action_history.record(
        action=action,
        user_id=user_id,
        user_name=user_name,
        chat_id=chat_id,
        chat_title=chat_title,
        success=success,
        message=msg_text,
    )

    if success:
        if action == "info" and res.get("data"):
            d = res["data"]
            mode_str = "Switch Mode" if d.get("switchMode") else "Press Mode"
            text = (
                f"✅ <b>SwitchBot Device Status</b>\n"
                f"🔋 Battery: <b>{d.get('battery')}%</b>\n"
                f"⚙️ Firmware: {d.get('firmware')}\n"
                f"📌 Mode: {mode_str}\n"
                f"⏱️ Hold time: {d.get('holdSeconds', 0)}s"
            )
        elif action == "long_press":
            text = f"✅ Long press executed successfully ({duration}s)!"
        else:
            text = f"✅ {msg_text}"
    else:
        text = f"❌ Error: {msg_text}"

    await status_msg.edit_text(text, parse_mode="HTML")


@dp.message(F.text == "🔘 Short Press")
@dp.message(Command("press"))
@dp.channel_post(Command("press"))
async def msg_press(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    chat_type = message.chat.type or "private"
    if not await is_user_authorized(bot, chat_id, user_id, chat_type):
        return
    await execute_and_respond(message, "press")


@dp.message(F.text.startswith("⏱️ Long Press"))
@dp.message(Command("longpress"))
@dp.channel_post(Command("longpress"))
@dp.message(Command("long_press"))
@dp.channel_post(Command("long_press"))
async def msg_long_press(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    chat_type = message.chat.type or "private"
    if not await is_user_authorized(bot, chat_id, user_id, chat_type):
        return
    duration = 5
    if message.text:
        parts = message.text.split()
        if len(parts) > 1 and parts[1].isdigit():
            duration = int(parts[1])
    await execute_and_respond(message, "long_press", duration=duration)


@dp.message(F.text == "🟢 Turn ON")
@dp.message(Command("on"))
@dp.channel_post(Command("on"))
async def msg_on(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    chat_type = message.chat.type or "private"
    if not await is_user_authorized(bot, chat_id, user_id, chat_type):
        return
    await execute_and_respond(message, "on")


@dp.message(F.text == "🔴 Turn OFF")
@dp.message(Command("off"))
@dp.channel_post(Command("off"))
async def msg_off(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    chat_type = message.chat.type or "private"
    if not await is_user_authorized(bot, chat_id, user_id, chat_type):
        return
    await execute_and_respond(message, "off")


@dp.message(F.text == "🔋 Battery & State")
@dp.message(Command("info"))
@dp.channel_post(Command("info"))
async def msg_info(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    chat_type = message.chat.type or "private"
    if not await is_user_authorized(bot, chat_id, user_id, chat_type):
        return
    await execute_and_respond(message, "info")


@dp.message(F.text == "❤️ Health")
@dp.message(Command("health"))
@dp.channel_post(Command("health"))
async def msg_health(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    chat_type = message.chat.type or "private"
    if not await is_user_authorized(bot, chat_id, user_id, chat_type):
        return
    stats = action_history.get_stats()
    sched = scheduler.get_status()
    text = (
        f"❤️ <b>Gateway Diagnostics & Health:</b>\n\n"
        f"• <b>Gateway Status:</b> 🟢 Operational (OK)\n"
        f"• <b>Bot Uptime:</b> {stats['uptime_seconds']}s (~{stats['uptime_seconds'] // 60} min)\n"
        f"• <b>Target MAC:</b> <code>{settings.switchbot_mac}</code>\n"
        f"• <b>BLE Lock:</b> <code>{settings.ble_lock_file}</code>\n"
        f"• <b>Workday Scheduler:</b> {'🟢 Enabled' if sched['enabled'] else '🔴 Disabled'}\n"
        f"• <b>Total Operations:</b> <b>{stats['total_actions']}</b> (Success: {stats['successes']})\n"
        f"• <b>Last Action:</b> <code>{stats['last_action_at'] or 'None'}</code>"
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(F.text == "📜 Action History")
@dp.message(Command("history"))
@dp.channel_post(Command("history"))
async def msg_history(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    chat_type = message.chat.type or "private"
    if not await is_user_authorized(bot, chat_id, user_id, chat_type):
        return
    text = action_history.format_telegram_history(limit=8)
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("schedule"))
@dp.channel_post(Command("schedule"))
async def msg_schedule(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    chat_type = message.chat.type or "private"
    if not await is_user_authorized(bot, chat_id, user_id, chat_type):
        return

    text_content = (message.text or "").strip().lower()
    parts = text_content.split()
    if len(parts) > 1:
        subcmd = parts[1]
        if subcmd in ["on", "start", "enable"]:
            scheduler.enable()
            await message.answer("🟢 Workday scheduler <b>enabled</b>!", parse_mode="HTML")
            return
        elif subcmd in ["off", "stop", "disable"]:
            scheduler.disable()
            await message.answer("🔴 Workday scheduler <b>paused</b>!", parse_mode="HTML")
            return

    text = scheduler.format_telegram_status()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Enable", callback_data="sched_on"),
                InlineKeyboardButton(text="🔴 Pause", callback_data="sched_off"),
            ]
        ]
    )
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery, bot: Bot):
    chat_id = callback.message.chat.id if callback.message else 0
    user_id = callback.from_user.id if callback.from_user else 0
    chat_type = callback.message.chat.type if callback.message else "private"

    if not await is_user_authorized(bot, chat_id, user_id, chat_type):
        await callback.answer("⛔ Access Denied", show_alert=True)
        return

    await callback.answer()
    data = callback.data

    if data in ["press", "long_press", "on", "off", "info"]:
        await execute_and_respond(callback, data)
    elif data == "health":
        stats = action_history.get_stats()
        sched = scheduler.get_status()
        text = (
            f"❤️ <b>Gateway Diagnostics & Health:</b>\n\n"
            f"• <b>Gateway:</b> 🟢 Operational (OK)\n"
            f"• <b>Uptime:</b> {stats['uptime_seconds']}s\n"
            f"• <b>Device MAC:</b> <code>{settings.switchbot_mac}</code>\n"
            f"• <b>Workday Scheduler:</b> {'🟢 Enabled' if sched['enabled'] else '🔴 Disabled'}\n"
            f"• <b>Total Operations:</b> <b>{stats['total_actions']}</b>\n"
            f"• <b>Last Action:</b> <code>{stats['last_action_at'] or 'None'}</code>"
        )
        if callback.message:
            await callback.message.answer(text, parse_mode="HTML")
    elif data == "history":
        text = action_history.format_telegram_history(limit=8)
        if callback.message:
            await callback.message.answer(text, parse_mode="HTML")
    elif data == "schedule":
        text = scheduler.format_telegram_status()
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🟢 Enable", callback_data="sched_on"),
                    InlineKeyboardButton(text="🔴 Pause", callback_data="sched_off"),
                ]
            ]
        )
        if callback.message:
            await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    elif data == "sched_on":
        scheduler.enable()
        if callback.message:
            await callback.message.answer("🟢 Workday scheduler <b>enabled</b>!", parse_mode="HTML")
    elif data == "sched_off":
        scheduler.disable()
        if callback.message:
            await callback.message.answer("🔴 Workday scheduler <b>paused</b>!", parse_mode="HTML")


async def run_bot():
    if not settings.telegram_bot_token:
        logger.info("No TELEGRAM_BOT_TOKEN provided. Telegram bot will not start.")
        return

    bot = Bot(token=settings.telegram_bot_token)
    logger.info("Starting Telegram Bot long-polling...")

    if settings.scheduler_enabled:
        logger.info("Starting background workday random scheduler...")
        scheduler.start_task()

    try:
        await dp.start_polling(
            bot,
            allowed_updates=["message", "edited_message", "channel_post", "edited_channel_post", "callback_query"]
        )
    finally:
        scheduler.stop()
        await bot.session.close()


def main():
    from app.logger import setup_logging
    setup_logging("switchbot-bot")
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN is not configured! Please specify it in .env or environment.")
        return
    logger.info("Starting SwitchBot Telegram Bot...")
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Telegram Bot stopped.")


if __name__ == "__main__":
    main()
