import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.events import EventBus, EventType, SecurityOperation
from ..infra.db.models import AgentRow, AuditLogRow, SecurityEventRow
from ..infra.repos.sqlalchemy import repository
from ..models.records import AuditLog, SecurityEvent
from ..schs.authz import Reason
from ..schs.monitoring import AuditEntry, EventFilters, SecurityEntry, Severity

_POLICY_FAILURES = frozenset({Reason.POLICY_INVALID, Reason.EXPLICIT_DENIAL, Reason.RESOURCE_OUT_OF_SCOPE,
                              Reason.NO_ACTIVE_POLICY, Reason.ROLE_DENIED, Reason.ACTION_NOT_GRANTED,
                              Reason.CONDITIONS_NOT_MET})
_ACTION = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*")


def _classification(event: SecurityOperation) -> tuple[str | None, Severity]:
    if event.event_type == EventType.INTEGRATION_ERROR or event.reason == Reason.ADAPTER_UNAVAILABLE:
        return "IntegrationError", "warning"
    if event.event_type == EventType.SUSPICIOUS_BEHAVIOUR:
        return ("RepeatedDeniedOperations" if event.reason == "repeated_denied_action" else "SuspiciousBehaviour"), "warning"
    if event.event_type not in {EventType.AUTHENTICATION_DENIED, EventType.ACTION_BLOCKED, EventType.ACCESS_CHECKED}:
        return None, "info"
    if event.reason == "credential_expired":
        return "ExpiredCredentialAttempt", "warning"
    if event.reason == Reason.SESSION_REVOKED:
        return "RevokedSessionAttempt", "warning"
    if event.reason == Reason.CAPABILITY_DENIED:
        return "CapabilityViolation", "warning"
    if event.reason in _POLICY_FAILURES:
        return "PolicyViolation", "warning"
    if event.event_type in {EventType.AUTHENTICATION_DENIED, EventType.ACTION_BLOCKED} or event.outcome == "denied":
        return "OperationDenied", "warning"
    return None, "info"


class AuditService:
    def __init__(self, session: Session, correlation_id: UUID) -> None:
        self._session = session
        self._correlation_id = correlation_id

    def persist(self, event: SecurityOperation) -> None:
        category, severity = _classification(event)
        owner_id = event.owner_id
        if event.actor_kind == "system" and event.agent_id is not None:
            owner_id = self._session.scalar(select(AgentRow.owner_id).where(AgentRow.id == event.agent_id))
        action = event.action
        if action is not None and (len(action) > 96 or _ACTION.fullmatch(action) is None):
            action = None
        audit = repository(self._session, AuditLog).add(AuditLog(
            event_type=event.event_type, owner_id=owner_id, actor_kind=event.actor_kind,
            actor_id=event.actor_id, agent_id=event.agent_id, session_id=event.session_id,
            action=action, resource_id=event.resource_id, request_id=event.request_id,
            outcome=event.outcome, reason=event.reason, correlation_id=self._correlation_id, severity=severity,
        ))
        if category is not None:
            repository(self._session, SecurityEvent).add(SecurityEvent(
                event_type=category, owner_id=owner_id, actor_kind=audit.actor_kind, actor_id=audit.actor_id,
                agent_id=audit.agent_id, session_id=audit.session_id, action=audit.action, resource_id=audit.resource_id,
                request_id=audit.request_id, outcome=audit.outcome, reason=audit.reason,
                correlation_id=audit.correlation_id, severity=severity, audit_event_id=audit.id,
            ))


def event_bus(session: Session, correlation_id: UUID) -> EventBus:
    return EventBus(AuditService(session, correlation_id).persist)


class EventQuery:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _rows(self, row: type[AuditLogRow] | type[SecurityEventRow], owner_id: UUID, filters: EventFilters):
        statement = select(row).where(row.owner_id == owner_id, row.correlation_id.is_not(None))
        if filters.since is not None:
            statement = statement.where(row.created_at >= filters.since)
        if filters.until is not None:
            statement = statement.where(row.created_at < filters.until)
        for column, value in ((row.agent_id, filters.agent_id), (row.event_type, filters.event_type),
                              (row.action, filters.action), (row.outcome, filters.decision),
                              (row.severity, filters.severity), (row.correlation_id, filters.correlation_id)):
            if value is not None:
                statement = statement.where(column == value)
        return self._session.scalars(statement.order_by(row.created_at.desc(), row.id.desc())
                                     .offset(filters.offset).limit(filters.limit))

    def audit(self, owner_id: UUID, filters: EventFilters) -> list[AuditEntry]:
        return [AuditEntry.model_validate(row) for row in self._rows(AuditLogRow, owner_id, filters)]

    def security(self, owner_id: UUID, filters: EventFilters) -> list[SecurityEntry]:
        return [SecurityEntry.model_validate(row) for row in self._rows(SecurityEventRow, owner_id, filters)]
