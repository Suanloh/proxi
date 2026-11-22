import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.errors import register_error_handlers
from .api.health import router as health_router
from .config import Settings, load_settings
from .infra.db.database import Database, database_url
from .logging_config import configure_logging

logger = logging.getLogger("proxi.app")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else load_settings()

    url = database_url(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.log_level)
        db = Database(url) if url is not None else None
        app.state.database = db
        try:
            logger.info("app.started", extra={"environment": settings.env})
            yield
        finally:
            if db is not None:
                db.close()

    app = FastAPI(title="PROXI API", version="0.1.0", lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(health_router, prefix="/api/v1")
    return app
