from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID, uuid4

from ..schs.authz import Outcome


class EventType(StrEnum):
    AGENT_REGISTERED = "AgentRegistered"
    AGENT_UPDATED = "AgentUpdated"
    AGENT_SUSPENDED = "AgentSuspended"
    AGENT_REVOKED = "AgentRevoked"
    SESSION_CREATED = "SessionCreated"
    SESSION_REVOKED = "SessionRevoked"
    CREDENTIAL_ISSUED = "CredentialIssued"
    CREDENTIAL_REVOKED = "CredentialRevoked"
    CAPABILITY_ISSUED = "CapabilityIssued"
    CAPABILITY_REVOKED = "CapabilityRevoked"
    POLICY_DRAFTED = "PolicyDrafted"
    POLICY_SUBMITTED = "PolicySubmitted"
    POLICY_SUPERSEDED = "PolicySuperseded"
    POLICY_APPROVED = "PolicyApproved"
    POLICY_REVOKED = "PolicyRevoked"
    ACTION_REQUESTED = "ActionRequested"
    ACTION_ALLOWED = "ActionAllowed"
    ACTION_HELD = "ActionHeld"
    ACTION_BLOCKED = "ActionBlocked"
    ACCESS_CHECKED = "AccessChecked"
    AUTHENTICATION_DENIED = "AuthenticationDenied"
    ACTION_EXECUTED = "ActionExecuted"
    APPROVAL_GRANTED = "ApprovalGranted"
    APPROVAL_REJECTED = "ApprovalRejected"
    APPROVAL_CANCELLED = "ApprovalCancelled"
    TRUST_SCORE_UPDATED = "TrustScoreUpdated"
    TRUST_REVIEWED = "TrustReviewed"
    SUSPICIOUS_BEHAVIOUR = "SuspiciousBehaviour"
    INTEGRATION_ERROR = "IntegrationError"


@dataclass(frozen=True, slots=True)
class SecurityOperation:
    event_type: EventType
    owner_id: UUID | None = None
    actor_kind: str = "anonymous"
    actor_id: UUID | None = None
    agent_id: UUID | None = None
    session_id: UUID | None = None
    action: str | None = None
    resource_id: UUID | None = None
    request_id: UUID | None = None
    outcome: str = "succeeded"
    reason: str | None = None


class EventBus:
    def __init__(self, *subscribers: Callable[[SecurityOperation], None]) -> None:
        self._subscribers = subscribers

    def publish(self, event: SecurityOperation) -> None:
        for subscriber in self._subscribers:
            subscriber(event)

    def owner(self, kind: EventType, owner_id: UUID, agent_id: UUID | None = None, *,
              session_id: UUID | None = None, resource_id: UUID | None = None, action: str | None = None,
              request_id: UUID | None = None, reason: str | None = None, outcome: str = "succeeded") -> None:
        self.publish(SecurityOperation(kind, owner_id, "owner", owner_id, agent_id, session_id,
                                       action, resource_id, request_id, outcome, reason))


_enforcement_correlation: ContextVar[UUID | None] = ContextVar("enforcement_correlation", default=None)


@contextmanager
def enforcement_correlation() -> Iterator[None]:
    token = _enforcement_correlation.set(uuid4())
    try:
        yield
    finally:
        _enforcement_correlation.reset(token)


def operation_correlation() -> UUID:
    return _enforcement_correlation.get() or uuid4()


NO_EVENTS = EventBus()
ACTION_EVENTS = {Outcome.ALLOW: EventType.ACTION_ALLOWED, Outcome.HOLD: EventType.ACTION_HELD,
                 Outcome.BLOCK: EventType.ACTION_BLOCKED}
