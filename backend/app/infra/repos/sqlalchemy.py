from dataclasses import fields
from datetime import datetime, timezone
from typing import Any, Generic, cast
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...core.repositories import AgentConflict, AgentRepository, MutableRecordRepository, RecordRepository, T
from ...models import records
from ..db import models

_PAIRS: dict[type[records.Record], type[models.Row]] = {
    records.User: models.UserRow,
    records.Agent: models.AgentRow,
    records.AgentSession: models.AgentSessionRow,
    records.Credential: models.CredentialRow,
    records.Capability: models.CapabilityRow,
    records.Task: models.TaskRow,
    records.IntentInterpretation: models.IntentInterpretationRow,
    records.Policy: models.PolicyRow,
    records.PolicyVersion: models.PolicyVersionRow,
    records.PolicyRule: models.PolicyRuleRow,
    records.ActionRequest: models.ActionRequestRow,
    records.AuthorizationDecision: models.AuthorizationDecisionRow,
    records.ApprovalRequest: models.ApprovalRequestRow,
    records.ApprovalRecord: models.ApprovalRecordRow,
    records.BehaviourEvent: models.BehaviourEventRow,
    records.TrustScore: models.TrustScoreRow,
    records.TrustEvent: models.TrustEventRow,
    records.AuditLog: models.AuditLogRow,
    records.SecurityEvent: models.SecurityEventRow,
    records.IntegrationConnection: models.IntegrationConnectionRow,
}
_APPEND_ONLY = frozenset({
    records.ActionRequest, records.AuthorizationDecision, records.ApprovalRequest, records.ApprovalRecord,
    records.BehaviourEvent, records.TrustEvent, records.AuditLog, records.SecurityEvent,
})
_MANAGED_FIELDS = frozenset({"id", "created_at", "updated_at"})


def _utc(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.utcoffset() is None:
            raise ValueError("Database timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)
    return value


class _Repository(Generic[T]):
    def __init__(self, session: Session, record_type: type[T]) -> None:
        self.session = session
        self.record_type = record_type
        self.row_type = _PAIRS[record_type]
        self.field_names = tuple(field.name for field in fields(record_type))

    def _record(self, row: models.Row) -> T:
        construct = cast(Any, self.record_type)
        return cast(T, construct(**{name: _utc(getattr(row, name)) for name in self.field_names}))

    def _values(self, record: T) -> dict[str, Any]:
        if type(record) is not self.record_type:
            raise TypeError("Repository received the wrong record type")
        return {name: _utc(getattr(record, name)) for name in self.field_names if name not in _MANAGED_FIELDS}

    def get(self, record_id: UUID) -> T | None:
        row = self.session.get(self.row_type, record_id)
        return self._record(row) if row is not None else None

    def add(self, record: T) -> T:
        row = self.row_type(id=record.id, **self._values(record))
        self.session.add(row)
        self.session.flush()
        return self._record(row)


class _MutableRepository(_Repository[T]):
    def update(self, record: T) -> T:
        values = self._values(record)
        row = self.session.get(self.row_type, record.id)
        if row is None:
            raise LookupError("Record not found")
        for name, value in values.items():
            setattr(row, name, value)
        self.session.flush()
        return self._record(row)


class _AgentRepository(_MutableRepository[records.Agent]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, records.Agent)

    def get_for_update(self, agent_id: UUID) -> records.Agent | None:
        row = self.session.get(models.AgentRow, agent_id, with_for_update=True, populate_existing=True)
        return self._record(row) if row is not None else None

    def list_owned(self, owner_id: UUID) -> list[records.Agent]:
        statement = select(models.AgentRow).where(models.AgentRow.owner_id == owner_id).order_by(
            models.AgentRow.created_at, models.AgentRow.id,
        )
        return [self._record(row) for row in self.session.scalars(statement)]

    def get_owned(self, owner_id: UUID, agent_id: UUID, *, for_update: bool = False) -> records.Agent | None:
        statement = select(models.AgentRow).where(
            models.AgentRow.owner_id == owner_id, models.AgentRow.id == agent_id,
        )
        if for_update:
            statement = statement.with_for_update().execution_options(populate_existing=True)
        row = self.session.scalar(statement)
        return self._record(row) if row is not None else None

    def add(self, record: records.Agent) -> records.Agent:
        try:
            return super().add(record)
        except IntegrityError as exc:
            self._raise_conflict(exc)
            raise

    def update(self, record: records.Agent) -> records.Agent:
        try:
            return super().update(record)
        except IntegrityError as exc:
            self._raise_conflict(exc)
            raise

    @staticmethod
    def _raise_conflict(exc: IntegrityError) -> None:
        cause = exc.orig
        if isinstance(cause, UniqueViolation) and cause.diag.constraint_name in {"pk_agents", "uq_agents_owner_id"}:
            raise AgentConflict("Agent ID or owner/name already exists") from None


def agent_repository(session: Session) -> AgentRepository:
    return _AgentRepository(session)


def repository(session: Session, record_type: type[T]) -> RecordRepository[T]:
    return _Repository(session, record_type)


def mutable_repository(session: Session, record_type: type[T]) -> MutableRecordRepository[T]:
    if record_type in _APPEND_ONLY:
        raise ValueError("History records are append-only")
    return _MutableRepository(session, record_type)
