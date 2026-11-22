from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from ..models.records import AgentSession
from ..svcs.access import MAX_SESSION_SECONDS, SessionStatus, session_status

Lifetime = Annotated[int, Field(strict=True, ge=1, le=MAX_SESSION_SECONDS)]
Scope = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)]


class AccessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionCreate(AccessRequest):
    ttl_seconds: Lifetime = MAX_SESSION_SECONDS


class SessionResponse(BaseModel):
    id: UUID
    agent_id: UUID
    status: SessionStatus
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None

    @classmethod
    def from_session(cls, session: AgentSession) -> "SessionResponse":
        return cls.model_validate({
            "id": session.id, "agent_id": session.agent_id, "status": session_status(session, datetime.now(UTC)),
            "created_at": session.created_at, "expires_at": session.expires_at, "revoked_at": session.revoked_at,
        })


class CredentialIssued(BaseModel):
    id: UUID
    token: str
    expires_at: datetime


class OperationScope(AccessRequest):
    task_id: UUID
    action: Scope
    resource: Scope


class CapabilityCreate(OperationScope):
    ttl_seconds: Lifetime = 300


class CapabilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    agent_id: UUID
    session_id: UUID
    task_id: UUID
    action: str
    resource: str
    expires_at: datetime


class AccessCheck(OperationScope):
    capability_id: UUID | None = None
