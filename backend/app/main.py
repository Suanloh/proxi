import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.errors import register_error_handlers
from .api.health import router as health_router
from .config import Settings, load_settings
from .logging_config import configure_logging

logger = logging.getLogger("proxi.app")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else load_settings()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.log_level)
        logger.info("app.started", extra={"environment": settings.env})
        yield

    app = FastAPI(title="PROXI API", version="0.1.0", lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(health_router, prefix="/api/v1")
    return app
