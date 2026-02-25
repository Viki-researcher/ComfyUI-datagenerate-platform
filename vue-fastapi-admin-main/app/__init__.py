import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from tortoise import Tortoise

from app.core.exceptions import SettingNotFound
from app.core.init_app import (
    init_data,
    make_middlewares,
    register_exceptions,
    register_routers,
)
from app.services.comfyui_history_sync import sync_loop
from app.services.comfyui_manager import heartbeat_loop

try:
    from app.settings.config import settings
except ImportError:
    raise SettingNotFound("Can not import settings")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_data()
    stop_event = asyncio.Event()
    hb_task = asyncio.create_task(heartbeat_loop(stop_event))
    sync_task = asyncio.create_task(sync_loop(stop_event, interval_seconds=int(settings.COMFYUI_HISTORY_SYNC_INTERVAL_SECONDS)))
    yield
    stop_event.set()
    hb_task.cancel()
    sync_task.cancel()
    with suppress(Exception):
        await hb_task
    with suppress(Exception):
        await sync_task
    await Tortoise.close_connections()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.VERSION,
        openapi_url="/openapi.json",
        middleware=make_middlewares(),
        lifespan=lifespan,
    )
    register_exceptions(app)
    register_routers(app, prefix="/api")
    return app


app = create_app()
