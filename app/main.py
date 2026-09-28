import asyncio
import logging
import uvicorn
from app.config import settings
from app.logger import setup_logging
from app.web import app
from app.bot import run_bot

setup_logging("switchbot-combined")
logger = logging.getLogger("main")


async def main():
    logger.info("Starting SwitchBot Gateway on %s:%s...", settings.web_host, settings.web_port)
    logger.info("Target SwitchBot MAC: %s", settings.switchbot_mac)

    server_config = uvicorn.Config(
        app,
        host=settings.web_host,
        port=settings.web_port,
        log_level="info"
    )
    server = uvicorn.Server(server_config)

    tasks = [asyncio.create_task(server.serve())]

    if settings.telegram_bot_token:
        logger.info("Telegram Bot token detected. Launching bot task...")
        tasks.append(asyncio.create_task(run_bot()))
    else:
        logger.info("Telegram Bot token not set. Running Web UI only.")

    try:
        await asyncio.gather(*tasks)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Shutdown requested.")
    finally:
        server.should_exit = True


if __name__ == "__main__":
    asyncio.run(main())
