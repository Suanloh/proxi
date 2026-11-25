from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .access import SessionStatus


class BrowserEvent(BaseModel):
    event_type: str
    action: str | None
    outcome: str | None
    reason: str | None
    created_at: datetime


class CapabilityScope(BaseModel):
    id: UUID
    action: str
    resource: str


class PendingApproval(BaseModel):
    id: UUID
    action: str
    expires_at: datetime


class WorkspaceStatus(BaseModel):
    agent_name: str
    agent_status: str
    session_status: SessionStatus
    session_expires_at: datetime
    task_name: str
    task_status: str
    configured: bool
    capabilities: list[CapabilityScope]
    pending_approvals: list[PendingApproval]
    events: list[BrowserEvent]


class CompanionPoll(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CompanionPairing(BaseModel):
    token: str
    expires_in: int


class CompanionStatus(BaseModel):
    controlled_browser: Literal["configured", "disabled"]
    operations: tuple[str, ...]
    events: list[BrowserEvent]
