import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.app.api import routes, ws as ws_routes
from backend.app.config import PROJECT_ROOT, get_settings
from backend.app.core.hotkeys import start_emergency_hotkey
from backend.app.logging_setup import setup_logging
from backend.app.plugins.loader import load_plugins
from backend.app.services import ChatRunner, build_services

log = logging.getLogger("nova.main")


def create_app(settings=None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level, PROJECT_ROOT / settings.log_dir)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        svcs = build_services(settings)
        app.state.services = svcs
        app.state.runner = ChatRunner(svcs)
        app.state.agent = svcs.agent

        def trigger_emergency():
            svcs.stop_event.set()
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(
                lambda: asyncio.create_task(app.state.runner.cancel_all())
            )

        start_emergency_hotkey(settings, trigger_emergency)
        loaded = load_plugins(svcs.registry, PROJECT_ROOT / "plugins")
        log.info("NOVA ready - %d tools (plugins: %s)", len(svcs.registry.all()), loaded or "-")

        yield

        svcs.browser.stop()
        svcs.db.close()
        log.info("NOVA shut down cleanly")

    app = FastAPI(title="NOVA", version="0.1.0", lifespan=lifespan)
    app.include_router(routes.router)
    app.websocket("/ws")(ws_routes.ws_endpoint)

    frontend_dir = PROJECT_ROOT / "frontend"
    if (frontend_dir / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

    return app


app = None


def get_app() -> FastAPI:
    global app
    if app is None:
        app = create_app()
    return app
