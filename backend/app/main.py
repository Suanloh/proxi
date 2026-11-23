import logging
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

from fastapi import FastAPI, HTTPException, Request
from sqlalchemy.orm import Session

from .api.access import create_access_router
from .api.agents import create_agents_router
from .api.approvals import create_approval_router
from .api.authz import create_authorization_router
from .api.errors import register_error_handlers
from .api.health import router as health_router
from .api.intent import create_intent_router
from .api.owner_auth import create_owner_auth
from .api.policies import create_policy_router
from .config import Settings, load_settings
from .core.creds.tokens import CredentialCodec
from .infra.creds.jwt import JwtCredentialCodec
from .infra.db.database import Database, database_url
from .infra.llm.deepseek import DeepSeekAdapter
from .infra.repos.approvals import approval_repository
from .infra.repos.sqlalchemy import agent_repository, mutable_repository, policy_repository, repository
from .logging_config import configure_logging
from .models.records import AgentSession, Capability, Credential, IntentInterpretation, Task, User
from .svcs.access import AgentAccessService
from .svcs.approvals import ActionApprovals
from .svcs.authz import AuthorizationEngine
from .svcs.identity import AgentIdentityService
from .svcs.intent import IntentInterpreter, IntentReview
from .svcs.policies import PolicyManagement
from .svcs.policy_checks import PolicyRetrieval

logger = logging.getLogger("proxi.app")


def access_service(session: Session, identity: AgentIdentityService, codec: CredentialCodec) -> AgentAccessService:
    return AgentAccessService(
        identity, mutable_repository(session, AgentSession), mutable_repository(session, Credential),
        mutable_repository(session, Capability), repository(session, Task), codec,
    )


@contextmanager
def authorization_transaction(db: Database, codec: CredentialCodec) -> Iterator[AuthorizationEngine]:
    with db.transaction() as session:
        identity = AgentIdentityService(agent_repository(session), repository(session, User))
        policies = PolicyRetrieval(policy_repository(session))
        yield AuthorizationEngine(identity, access_service(session, identity, codec), policies,
                                  approvals=ActionApprovals(approval_repository(session), identity, policies))


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
            identity = AgentIdentityService(agent_repository(session), repository(session, User))
            yield access_service(session, identity, codec)

    @contextmanager
    def authorization_check_transaction(request: Request) -> Iterator[AuthorizationEngine]:
        db: Database | None = request.app.state.database
        if db is None or codec is None:
            raise HTTPException(status_code=503)
        with authorization_transaction(db, codec) as engine:
            yield engine

    @contextmanager
    def approval_transaction(request: Request) -> Iterator[ActionApprovals]:
        db: Database | None = request.app.state.database
        if db is None:
            raise HTTPException(status_code=503)
        with db.transaction() as session:
            identity = AgentIdentityService(agent_repository(session), repository(session, User))
            yield ActionApprovals(approval_repository(session), identity, PolicyRetrieval(policy_repository(session)))

    @contextmanager
    def intent_transaction(request: Request) -> Iterator[IntentReview]:
        db: Database | None = request.app.state.database
        if db is None:
            raise HTTPException(status_code=503)
        with db.transaction() as session:
            yield IntentReview(
                AgentIdentityService(agent_repository(session), repository(session, User)),
                repository(session, Task), repository(session, IntentInterpretation),
            )

    @contextmanager
    def policy_transaction(request: Request) -> Iterator[PolicyManagement]:
        db: Database | None = request.app.state.database
        if db is None:
            raise HTTPException(status_code=503)
        with db.transaction() as session:
            identity = AgentIdentityService(agent_repository(session), repository(session, User))
            intents = IntentReview(identity, repository(session, Task), repository(session, IntentInterpretation))
            yield PolicyManagement(identity, intents, policy_repository(session))

    interpreter = IntentInterpreter(DeepSeekAdapter(
        settings.deepseek_api_key, settings.deepseek_model, settings.deepseek_timeout_seconds,
    ))
    app = FastAPI(title="PROXI API", version="0.1.0", lifespan=lifespan)
    register_error_handlers(app)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(create_agents_router(authenticate_owner, identity_transaction), prefix="/api/v1")
    app.include_router(create_access_router(authenticate_owner, access_transaction), prefix="/api/v1")
    app.include_router(create_authorization_router(codec, authorization_check_transaction), prefix="/api/v1")
    app.include_router(create_intent_router(authenticate_owner, intent_transaction, interpreter), prefix="/api/v1")
    app.include_router(create_policy_router(authenticate_owner, policy_transaction), prefix="/api/v1")
    app.include_router(create_approval_router(authenticate_owner, approval_transaction), prefix="/api/v1")
    return app
