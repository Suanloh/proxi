import logging
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

from fastapi import FastAPI, HTTPException, Request

from .api.access import create_access_router
from .api.agents import create_agents_router
from .api.errors import register_error_handlers
from .api.health import router as health_router
from .api.owner_auth import create_owner_auth
from .config import Settings, load_settings
from .infra.creds.jwt import JwtCredentialCodec
from .infra.db.database import Database, database_url
from .infra.repos.sqlalchemy import agent_repository, mutable_repository, repository
from .logging_config import configure_logging
from .models.records import AgentSession, Capability, Credential, Task, User
from .svcs.access import AgentAccessService
from .svcs.identity import AgentIdentityService

logger = logging.getLogger("proxi.app")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else load_settings()

    url = database_url(settings)
    codec = JwtCredentialCodec(settings.credential_signing_key) if settings.credential_signing_key is not None else None
    authenticate_owner = create_owner_auth(settings.dev_identity_owner_id, settings.dev_identity_token)

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

    @contextmanager
    def identity_transaction(request: Request) -> Iterator[AgentIdentityService]:
        db: Database | None = request.app.state.database
        if db is None:
            raise HTTPException(status_code=503)
        with db.transaction() as session:
            yield AgentIdentityService(agent_repository(session), repository(session, User))

    @contextmanager
    def access_transaction(request: Request) -> Iterator[AgentAccessService]:
        db: Database | None = request.app.state.database
        if db is None or codec is None:
            raise HTTPException(status_code=503)
        with db.transaction() as session:
            yield AgentAccessService(
                AgentIdentityService(agent_repository(session), repository(session, User)),
                mutable_repository(session, AgentSession), mutable_repository(session, Credential),
                mutable_repository(session, Capability), repository(session, Task), codec,
            )

    app = FastAPI(title="PROXI API", version="0.1.0", lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(create_agents_router(authenticate_owner, identity_transaction), prefix="/api/v1")
    app.include_router(create_access_router(authenticate_owner, access_transaction), prefix="/api/v1")
    return app
