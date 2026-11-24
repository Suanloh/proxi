import logging
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Request
from sqlalchemy.orm import Session

from .api.access import create_access_router
from .api.agents import create_agents_router
from .api.approvals import create_approval_router
from .api.authz import create_authorization_router
from .api.browser import create_browser_router
from .api.dashboard import create_dashboard_router
from .svcs.dashboard import DashboardQuery, integration_status
from .api.errors import register_error_handlers
from .api.health import router as health_router
from .api.integrations import create_integration_router
from .api.intent import create_intent_router
from .api.monitoring import create_monitoring_router
from .api.owner_auth import create_owner_auth
from .api.policies import create_policy_router
from .api.trust import create_trust_router
from .config import Settings, load_settings
from .core.creds.tokens import CredentialClaims, CredentialCodec
from .core.events import NO_EVENTS, EventBus, EventType, operation_correlation
from .core.trust.rules import TrustRules
from .infra.creds.jwt import JwtCredentialCodec
from .infra.db.database import Database, database_url
from .infra.llm.deepseek import DeepSeekAdapter
from .infra.repos.approvals import approval_repository
from .infra.repos.sqlalchemy import agent_repository, mutable_repository, policy_repository, repository
from .infra.repos.trust import SqlTrustHistory
from .integrations.browser.playwright import PlaywrightBrowser
from .integrations.local_agent.catalog import LocalCatalogAdapter
from .integrations.mcp.gateway import McpCatalogGateway
from .logging_config import configure_logging
from .models.records import AgentSession, Capability, Credential, IntentInterpretation, Task, User
from .svcs.access import AgentAccessService
from .svcs.approvals import ActionApprovals
from .svcs.authz import AuthorizationEngine
from .svcs.identity import AgentIdentityService
from .svcs.integrations import LOCAL_CATALOG, MCP_CATALOG, IntegrationRegistry
from .svcs.intent import IntentInterpreter, IntentReview
from .svcs.monitoring import EventQuery, event_bus
from .svcs.policies import PolicyManagement
from .svcs.policy_checks import PolicyRetrieval
from .svcs.trust import DynamicTrust

logger = logging.getLogger("proxi.app")


def access_service(session: Session, identity: AgentIdentityService, codec: CredentialCodec) -> AgentAccessService:
    return AgentAccessService(
        identity, mutable_repository(session, AgentSession), mutable_repository(session, Credential),
        mutable_repository(session, Capability), repository(session, Task), codec,
    )


def trust_service(session: Session, rules: TrustRules, events: EventBus = NO_EVENTS) -> DynamicTrust:
    return DynamicTrust(SqlTrustHistory(session), repository(session, IntentInterpretation), rules, events=events)


@contextmanager
def authorization_transaction(db: Database, codec: CredentialCodec,
                              rules: TrustRules | None = None, *,
                              correlation_id: UUID | None = None) -> Iterator[AuthorizationEngine]:
    with db.transaction() as session:
        events = event_bus(session, correlation_id or operation_correlation())
        identity = AgentIdentityService(agent_repository(session), repository(session, User), events=events)
        policies = PolicyRetrieval(policy_repository(session))
        trust = trust_service(session, rules if rules is not None else TrustRules(), events)
        approvals = ActionApprovals(approval_repository(session), identity, policies, on_created=trust.approval_created)
        yield AuthorizationEngine(identity, access_service(session, identity, codec), policies,
                                  trust=trust, behaviour=trust, approvals=approvals)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else load_settings()

    url = database_url(settings)
    codec = JwtCredentialCodec(settings.credential_signing_key) if settings.credential_signing_key is not None else None
    def identity_service(session: Session, request: Request) -> AgentIdentityService:
        return AgentIdentityService(agent_repository(session), repository(session, User),
                                    events=event_bus(session, request.state.correlation_id))

    def record_credential_denial(request: Request, claims: CredentialClaims | None = None) -> None:
        db: Database | None = request.app.state.database
        if db is None or codec is None:
            return
        with db.transaction() as session:
            access = access_service(session, identity_service(session, request), codec)
            agent = access.audit_agent(claims) if claims is not None else None
            access.record_attempt(EventType.AUTHENTICATION_DENIED, agent, claims.session_id if claims else None,
                                  None, "denied", "credential_expired" if agent else "credential_invalid")

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
            yield identity_service(session, request)

    @contextmanager
    def access_transaction(request: Request) -> Iterator[AgentAccessService]:
        db: Database | None = request.app.state.database
        if db is None or codec is None:
            raise HTTPException(status_code=503)
        with db.transaction() as session:
            identity = identity_service(session, request)
            yield access_service(session, identity, codec)

    @contextmanager
    def authorization_check_transaction(request: Request) -> Iterator[AuthorizationEngine]:
        db: Database | None = request.app.state.database
        if db is None or codec is None:
            raise HTTPException(status_code=503)
        with authorization_transaction(db, codec, settings.trust_rules,
                                       correlation_id=request.state.correlation_id) as engine:
            yield engine

    @contextmanager
    def approval_transaction(request: Request) -> Iterator[ActionApprovals]:
        db: Database | None = request.app.state.database
        if db is None:
            raise HTTPException(status_code=503)
        with db.transaction() as session:
            identity = identity_service(session, request)
            yield ActionApprovals(approval_repository(session), identity, PolicyRetrieval(policy_repository(session)))

    @contextmanager
    def trust_transaction(request: Request) -> Iterator[tuple[DynamicTrust, AgentIdentityService]]:
        db: Database | None = request.app.state.database
        if db is None:
            raise HTTPException(status_code=503)
        with db.transaction() as session:
            identity = identity_service(session, request)
            yield trust_service(session, settings.trust_rules, identity.events), identity

    @contextmanager
    def intent_transaction(request: Request) -> Iterator[IntentReview]:
        db: Database | None = request.app.state.database
        if db is None:
            raise HTTPException(status_code=503)
        with db.transaction() as session:
            yield IntentReview(
                identity_service(session, request),
                repository(session, Task), repository(session, IntentInterpretation),
            )

    @contextmanager
    def policy_transaction(request: Request) -> Iterator[PolicyManagement]:
        db: Database | None = request.app.state.database
        if db is None:
            raise HTTPException(status_code=503)
        with db.transaction() as session:
            identity = identity_service(session, request)
            intents = IntentReview(identity, repository(session, Task), repository(session, IntentInterpretation))
            yield PolicyManagement(identity, intents, policy_repository(session))

    @contextmanager
    def query_transaction(request: Request, owner_id: UUID) -> Iterator[EventQuery]:
        db: Database | None = request.app.state.database
        if db is None:
            raise HTTPException(status_code=503)
        with db.transaction() as session:
            identity_service(session, request).require_active_owner(owner_id)
            yield EventQuery(session)

    @contextmanager
    def dashboard_transaction(request: Request) -> Iterator[tuple[DashboardQuery, AgentIdentityService]]:
        db: Database | None = request.app.state.database
        if db is None:
            raise HTTPException(status_code=503)
        with db.transaction() as session:
            yield DashboardQuery(session, settings.trust_rules), identity_service(session, request)

    interpreter = IntentInterpreter(DeepSeekAdapter(
        settings.deepseek_api_key, settings.deepseek_model, settings.deepseek_timeout_seconds,
    ))
    app = FastAPI(title="PROXI API", version="0.1.0", lifespan=lifespan)
    @app.middleware("http")
    async def correlate(request: Request, call_next):
        correlation_id = uuid4()
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = str(correlation_id)
        return response

    register_error_handlers(app)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(create_agents_router(authenticate_owner, identity_transaction), prefix="/api/v1")
    app.include_router(create_access_router(authenticate_owner, access_transaction, record_credential_denial), prefix="/api/v1")
    app.include_router(create_authorization_router(codec, authorization_check_transaction, record_credential_denial), prefix="/api/v1")
    browser = PlaywrightBrowser(settings.browser_allowed_pages, settings.browser_denied_pages)
    app.include_router(create_browser_router(browser, codec, authorization_check_transaction,
                                             record_credential_denial), prefix="/api/v1")
    integrations = IntegrationRegistry()
    integrations.register(MCP_CATALOG, McpCatalogGateway())
    integrations.register(LOCAL_CATALOG, LocalCatalogAdapter())
    if settings.mcp_catalog_enabled:
        integrations.enable(MCP_CATALOG)
    if settings.local_catalog_enabled:
        integrations.enable(LOCAL_CATALOG)
    app.state.integrations = integrations
    app.include_router(create_integration_router(integrations, codec, authorization_check_transaction,
                                                 record_credential_denial), prefix="/api/v1")
    app.include_router(create_intent_router(authenticate_owner, intent_transaction, interpreter), prefix="/api/v1")
    app.include_router(create_policy_router(authenticate_owner, policy_transaction), prefix="/api/v1")
    app.include_router(create_approval_router(authenticate_owner, approval_transaction), prefix="/api/v1")
    app.include_router(create_trust_router(authenticate_owner, trust_transaction), prefix="/api/v1")
    app.include_router(create_monitoring_router(authenticate_owner, query_transaction), prefix="/api/v1")
    app.include_router(create_dashboard_router(authenticate_owner, dashboard_transaction,
                                               lambda: integration_status(browser, integrations)), prefix="/api/v1")
    return app
