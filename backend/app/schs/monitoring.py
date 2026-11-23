from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from .authz import Outcome
from .intent import Action

Severity = Literal["info", "warning", "critical"]


class EventFilters(BaseModel):
    since: AwareDatetime | None = None
    until: AwareDatetime | None = None
    agent_id: UUID | None = None
    event_type: Annotated[str, Field(max_length=64)] | None = None
    action: Action | None = None
    decision: Outcome | None = None
    severity: Severity | None = None
    correlation_id: UUID | None = None
    limit: Annotated[int, Field(ge=1, le=100)] = 50
    offset: Annotated[int, Field(ge=0, le=10000)] = 0

    @model_validator(mode="after")
    def ordered_times(self) -> Self:
        if self.since is not None and self.until is not None and self.since >= self.until:
            raise ValueError("since must precede until")
        return self


class AuditEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    actor_kind: str
    actor_id: UUID | None
    agent_id: UUID | None
    session_id: UUID | None
    action: str | None
    resource_id: UUID | None
    request_id: UUID | None
    outcome: str
    reason: str | None
    created_at: AwareDatetime
    correlation_id: UUID
    severity: Severity


class SecurityEntry(AuditEntry):
    audit_event_id: UUID
