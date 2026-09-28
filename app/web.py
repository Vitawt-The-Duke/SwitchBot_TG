from pathlib import Path
import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.switchbot_client import bot_client
from app.history import action_history
from app.scheduler import scheduler

logger = logging.getLogger("web")

app = FastAPI(title="SwitchBot Gateway API")

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"mac": settings.switchbot_mac}
    )


@app.get("/api/health")
async def health_check():
    stats = action_history.get_stats()
    sched = scheduler.get_status()
    return {
        "status": "ok",
        "mac": settings.switchbot_mac,
        "uptime_seconds": stats["uptime_seconds"],
        "ble_lock_file": settings.ble_lock_file,
        "total_actions": stats["total_actions"],
        "scheduler": sched,
    }


@app.post("/api/press")
async def api_press():
    res = await bot_client.press(duration=0)
    action_history.record(
        action="press",
        user_id="web",
        user_name="Web Dashboard",
        success=res.get("success", False),
        message=f"Web press: {res.get('message', '')}",
    )
    return res


@app.post("/api/longpress")
async def api_long_press(duration: int = 5):
    res = await bot_client.long_press(duration=duration)
    action_history.record(
        action="long_press",
        user_id="web",
        user_name="Web Dashboard",
        success=res.get("success", False),
        message=f"Web long press ({duration}s): {res.get('message', '')}",
    )
    return res


@app.post("/api/on")
async def api_turn_on():
    res = await bot_client.turn_on()
    action_history.record(
        action="on",
        user_id="web",
        user_name="Web Dashboard",
        success=res.get("success", False),
        message=f"Web turn ON: {res.get('message', '')}",
    )
    return res


@app.post("/api/off")
async def api_turn_off():
    res = await bot_client.turn_off()
    action_history.record(
        action="off",
        user_id="web",
        user_name="Web Dashboard",
        success=res.get("success", False),
        message=f"Web turn OFF: {res.get('message', '')}",
    )
    return res


@app.get("/api/info")
async def api_info():
    res = await bot_client.get_info()
    action_history.record(
        action="info",
        user_id="web",
        user_name="Web Dashboard",
        success=res.get("success", False),
        message="Web status request",
    )
    return res


@app.get("/api/history")
async def api_history(limit: int = 20):
    return {
        "history": action_history.get_recent(limit=limit),
        "stats": action_history.get_stats(),
    }


@app.get("/api/schedule")
async def api_schedule():
    return scheduler.get_status()


def main():
    import uvicorn
    from app.logger import setup_logging

    setup_logging("switchbot-web")
    logger.info("Starting SwitchBot Web UI on %s:%s...", settings.web_host, settings.web_port)
    uvicorn.run(app, host=settings.web_host, port=settings.web_port, log_level="info")


if __name__ == "__main__":
    main()
