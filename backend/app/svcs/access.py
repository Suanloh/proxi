from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from ..core.creds.tokens import CredentialClaims, CredentialCodec, InvalidCredential
from ..core.identity.lifecycle import InvalidAgentStatus, require_active
from ..core.repositories import MutableRecordRepository, RecordRepository
from ..models.records import AgentSession, Capability, Credential, Task
from .identity import AgentIdentityService, AgentNotFound, OwnerNotAuthorized

MAX_SESSION_SECONDS = 3600
CREDENTIAL_SECONDS = 300
SessionStatus = Literal["active", "expired", "revoked"]


class AccessRecordNotFound(LookupError):
    pass


class InvalidSession(ValueError):
    pass


class CapabilityDenied(PermissionError):
    pass


def session_status(session: AgentSession, now: datetime) -> SessionStatus:
    if session.revoked_at is not None:
        return "revoked"
    return "expired" if session.expires_at <= now else "active"


class AgentAccessService:
    def __init__(
        self, identity: AgentIdentityService, sessions: MutableRecordRepository[AgentSession],
        credentials: MutableRecordRepository[Credential], capabilities: MutableRecordRepository[Capability],
        tasks: RecordRepository[Task], codec: CredentialCodec, clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._identity = identity
        self._sessions = sessions
        self._credentials = credentials
        self._capabilities = capabilities
        self._tasks = tasks
        self._codec = codec
        self._clock = clock

    def _owned_agent(self, owner_id: UUID, agent_id: UUID, *, active: bool = False) -> None:
        self._identity.require_active_owner(owner_id)
        # Take the same agent row lock for mutations and prerequisite checks.
        agent = self._identity.get_owned(owner_id, agent_id, for_update=True)
        if active:
            require_active(agent.status)

    @staticmethod
    def _require_session(session: AgentSession, now: datetime) -> None:
        if session_status(session, now) != "active":
            raise InvalidSession("Session is not active")

    def create_session(self, owner_id: UUID, agent_id: UUID, ttl_seconds: int) -> AgentSession:
        if not 1 <= ttl_seconds <= MAX_SESSION_SECONDS:
            raise ValueError("Invalid session lifetime")
        self._owned_agent(owner_id, agent_id, active=True)
        return self._sessions.add(AgentSession(agent_id=agent_id, expires_at=self._clock() + timedelta(seconds=ttl_seconds)))

    def get_session(self, owner_id: UUID, agent_id: UUID, session_id: UUID) -> AgentSession:
        self._owned_agent(owner_id, agent_id)
        return self.get_bound_session(agent_id, session_id)

    def revoke_session(self, owner_id: UUID, agent_id: UUID, session_id: UUID) -> AgentSession:
        session = self.get_session(owner_id, agent_id, session_id)
        if session.revoked_at is None:
            session = self._sessions.update(replace(session, revoked_at=self._clock()))
        return session

    def issue_credential(self, owner_id: UUID, agent_id: UUID, session_id: UUID) -> tuple[Credential, str]:
        self._owned_agent(owner_id, agent_id, active=True)
        session = self.get_bound_session(agent_id, session_id)
        now = self._clock()
        self._require_session(session, now)
        expires = int(min(session.expires_at, now + timedelta(seconds=CREDENTIAL_SECONDS)).timestamp())
        if expires <= now.timestamp():
            raise InvalidSession("Session expires too soon to issue a credential")
        credential_id = uuid4()
        token = self._codec.encode(CredentialClaims(agent_id, session_id, credential_id, int(now.timestamp()), expires))
        entry = self._credentials.add(Credential(
            id=credential_id, agent_id=agent_id, session_id=session_id,
            secret_ref=f"jwt:{credential_id}", expires_at=datetime.fromtimestamp(expires, UTC),
        ))
        return entry, token

    def revoke_credential(self, owner_id: UUID, agent_id: UUID, session_id: UUID, credential_id: UUID) -> None:
        self.get_session(owner_id, agent_id, session_id)
        entry = self._credentials.get(credential_id)
        if entry is None or (entry.agent_id, entry.session_id) != (agent_id, session_id):
            raise AccessRecordNotFound("Credential not found")
        if entry.revoked_at is None:
            self._credentials.update(replace(entry, revoked_at=self._clock()))

    def _task(self, agent_id: UUID, task_id: UUID) -> Task:
        task = self._tasks.get(task_id)
        if task is None or task.agent_id != agent_id:
            raise AccessRecordNotFound("Task not found")
        return task

    def grant_capability(
        self, owner_id: UUID, agent_id: UUID, session_id: UUID, task_id: UUID,
        action: str, resource: str, ttl_seconds: int,
    ) -> Capability:
        if not 1 <= ttl_seconds <= MAX_SESSION_SECONDS or not action.strip() or not resource.strip():
            raise ValueError("Invalid capability scope or lifetime")
        self._owned_agent(owner_id, agent_id, active=True)
        session = self.get_bound_session(agent_id, session_id)
        if self._task(agent_id, task_id).status != "pending":
            raise CapabilityDenied("Task is not pending")
        now = self._clock()
        self._require_session(session, now)
        return self._capabilities.add(Capability(
            agent_id=agent_id, session_id=session_id, task_id=task_id, action=action, resource=resource,
            expires_at=min(session.expires_at, now + timedelta(seconds=ttl_seconds)),
        ))

    def revoke_capability(self, owner_id: UUID, agent_id: UUID, session_id: UUID, capability_id: UUID) -> None:
        self.get_session(owner_id, agent_id, session_id)
        capability = self._capabilities.get(capability_id)
        if capability is None or (capability.agent_id, capability.session_id) != (agent_id, session_id):
            raise AccessRecordNotFound("Capability not found")
        if capability.revoked_at is None:
            self._capabilities.update(replace(capability, revoked_at=self._clock()))

    def require_access(
        self, token: str, *, agent_id: UUID, session_id: UUID, capability_id: UUID | None,
        task_id: UUID, action: str, resource: str,
    ) -> None:
        """Validate prerequisites; this does not authorize or execute the operation."""
        claims = self.decode_bound_credential(token, agent_id, session_id)
        try:
            agent = self._identity.validate_active(agent_id, for_update=True)
            self._identity.require_active_owner(agent.owner_id)
            now = self._clock()
            self._require_session(self.get_bound_session(agent_id, session_id), now)
        except (AgentNotFound, OwnerNotAuthorized, InvalidAgentStatus, AccessRecordNotFound, InvalidSession):
            raise InvalidCredential("Agent or session is not active") from None
        self.require_current_credential(claims, now)
        self.require_capability(agent_id, session_id, capability_id, task_id, action, resource, self._clock())

    def get_bound_session(self, agent_id: UUID, session_id: UUID) -> AgentSession:
        session = self._sessions.get(session_id)
        if session is None or session.agent_id != agent_id:
            raise AccessRecordNotFound("Session not found")
        return session

    def decode_bound_credential(self, token: str, agent_id: UUID, session_id: UUID) -> CredentialClaims:
        claims = self._codec.decode(token)
        if (claims.agent_id, claims.session_id) != (agent_id, session_id):
            raise InvalidCredential("Credential binding mismatch")
        return claims

    def require_current_credential(self, claims: CredentialClaims, now: datetime) -> None:
        entry = self._credentials.get(claims.credential_id)
        if (
            entry is None or (entry.agent_id, entry.session_id) != (claims.agent_id, claims.session_id)
            or entry.revoked_at is not None or entry.expires_at is None or entry.expires_at <= now
            or claims.expires_at != entry.expires_at.timestamp()
        ):
            raise InvalidCredential("Credential is not active")

    def require_capability(
        self, agent_id: UUID, session_id: UUID, capability_id: UUID | None, task_id: UUID | None,
        action: str, resource: str, now: datetime,
    ) -> None:
        if task_id is None:
            raise CapabilityDenied("A task-bound capability is required")
        capability = self._capabilities.get(capability_id) if capability_id is not None else None
        if (
            capability is None or (capability.agent_id, capability.session_id, capability.task_id)
            != (agent_id, session_id, task_id) or (capability.action, capability.resource) != (action, resource)
            or capability.revoked_at is not None or capability.expires_at is None or capability.expires_at <= now
        ):
            raise CapabilityDenied("Capability does not cover this operation")
        try:
            if self._task(agent_id, task_id).status == "pending":
                return
        except AccessRecordNotFound:
            pass
        raise CapabilityDenied("Capability does not cover an active task")
