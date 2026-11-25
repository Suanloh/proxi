from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from hmac import compare_digest
from secrets import token_urlsafe
from threading import Lock
from time import monotonic
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.creds.tokens import CredentialCodec, ExpiredCredential, InvalidCredential
from ..infra.db.models import CapabilityRow, TaskRow
from ..integrations.browser.playwright import SUPPORTED_ACTIONS
from ..models.records import AgentType
from ..schs.browser_experience import CompanionPairing, CompanionPoll, CompanionStatus, WorkspaceStatus
from ..svcs.access import AccessRecordNotFound, AgentAccessService, session_status
from ..svcs.browser_experience import browser_events, task_scope
from ..svcs.identity import AgentIdentityService, AgentNotFound, OwnerNotAuthorized
from .dashboard import require_owner
from .owner_auth import bearer_required

_LOCAL_HOST = "127.0.0.1:8000"
_PAIRING_SECONDS = 300


class CompanionGrant:
    def __init__(self) -> None:
        self._lock = Lock()
        self._grant: tuple[UUID, str, float] | None = None

    def issue(self, owner: UUID) -> CompanionPairing:
        token = token_urlsafe(32)
        with self._lock:
            self._grant = (owner, token, monotonic() + _PAIRING_SECONDS)
        return CompanionPairing(token=token, expires_in=_PAIRING_SECONDS)

    def owner(self, token: str) -> UUID:
        with self._lock:
            if self._grant is not None:
                owner, expected, expiry = self._grant
                if monotonic() >= expiry:
                    self._grant = None
                elif len(token) == len(expected) and compare_digest(token.encode(), expected.encode()):
                    return owner
        raise bearer_required()


def create_browser_experience_router(
    authenticate_owner: Callable[..., UUID],
    transaction: Callable[[Request], AbstractContextManager[tuple[Session, AgentIdentityService]]],
    access_service: Callable[[Session, AgentIdentityService, CredentialCodec], AgentAccessService],
    codec: CredentialCodec | None, configured: Callable[[], bool], extension_id: str | None,
) -> APIRouter:
    router = APIRouter(prefix="/browser", tags=["browser experience"])
    grant = CompanionGrant()
    owner_auth = Depends(authenticate_owner)
    agent_auth = Depends(HTTPBearer(auto_error=False, scheme_name="AgentBearer", bearerFormat="JWT"))
    companion_auth = Depends(HTTPBearer(auto_error=False, scheme_name="CompanionBearer"))
    expected_origin = f"chrome-extension://{extension_id}" if extension_id else None

    @router.get("/workspace/{agent_id}/{session_id}/{task_id}")
    def workspace(agent_id: UUID, session_id: UUID, task_id: UUID, request: Request, response: Response,
                  credentials: Annotated[HTTPAuthorizationCredentials | None, agent_auth]) -> WorkspaceStatus:
        if credentials is None or len(credentials.credentials) > 2048:
            raise bearer_required()
        if codec is None:
            raise HTTPException(status_code=503)
        now = datetime.now(UTC)
        with transaction(request) as (db, identity):
            access = access_service(db, identity, codec)
            try:
                claims = access.decode_bound_credential(credentials.credentials, agent_id, session_id)
                access.require_current_credential(claims, now)
                session = access.get_bound_session(agent_id, session_id)
                agent = identity.resolve(agent_id)
                identity.require_active_owner(agent.owner_id)
            except (InvalidCredential, ExpiredCredential, AccessRecordNotFound, AgentNotFound, OwnerNotAuthorized):
                raise bearer_required() from None
            task = db.get(TaskRow, task_id)
            bound = db.scalar(select(CapabilityRow.id).where(
                CapabilityRow.agent_id == agent_id, CapabilityRow.session_id == session_id,
                CapabilityRow.task_id == task_id, CapabilityRow.action.startswith("browser."),
            ).limit(1))
            if agent.type != AgentType.BROWSER or task is None or task.agent_id != agent_id or bound is None:
                raise HTTPException(status_code=404)
            caps, pending = task_scope(db, agent.owner_id, agent_id, session_id, task)
            response.headers["Cache-Control"] = "no-store"
            return WorkspaceStatus(agent_name=agent.name, agent_status=agent.status,
                                   session_status=session_status(session, now), session_expires_at=session.expires_at,
                                   task_name=task.objective, task_status=task.status, configured=configured(),
                                   capabilities=caps, pending_approvals=pending,
                                   events=browser_events(db, agent.owner_id, session_id))

    def local_request(request: Request, origin: str | None) -> None:
        origins = request.headers.getlist("origin")
        if (expected_origin is None or request.headers.getlist("host") != [_LOCAL_HOST]
                or origins != ([origin] if origin else []) or request.url.query):
            raise HTTPException(status_code=403)

    @router.post("/companion/pairing")
    def pairing(request: Request, response: Response, owner: Annotated[UUID, owner_auth],
                _body: CompanionPoll) -> CompanionPairing:
        local_request(request, None)
        with transaction(request) as (_, identity):
            require_owner(identity, owner)
        response.headers["Cache-Control"] = "no-store"
        return grant.issue(owner)

    @router.post("/companion/status")
    def companion(request: Request, response: Response, _body: CompanionPoll,
                  credentials: Annotated[HTTPAuthorizationCredentials | None, companion_auth]) -> CompanionStatus:
        local_request(request, expected_origin)
        if credentials is None:
            raise bearer_required()
        owner = grant.owner(credentials.credentials)
        with transaction(request) as (db, identity):
            require_owner(identity, owner)
            events = browser_events(db, owner)
        response.headers["Cache-Control"] = "no-store"
        return CompanionStatus(controlled_browser="configured" if configured() else "disabled",
                               operations=SUPPORTED_ACTIONS, events=events)

    return router
