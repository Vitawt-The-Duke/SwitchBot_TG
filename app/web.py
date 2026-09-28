from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.switchbot_client import bot_client

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
    return {"status": "ok", "mac": settings.switchbot_mac}


@app.post("/api/press")
async def api_press():
    return await bot_client.press()


@app.post("/api/on")
async def api_turn_on():
    return await bot_client.turn_on()


@app.post("/api/off")
async def api_turn_off():
    return await bot_client.turn_off()


@app.get("/api/info")
async def api_info():
    return await bot_client.get_info()


def main():
    import logging
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logger = logging.getLogger("web")
    logger.info("Starting SwitchBot Web UI on %s:%s...", settings.web_host, settings.web_port)
    uvicorn.run(app, host=settings.web_host, port=settings.web_port, log_level="info")


if __name__ == "__main__":
    main()
