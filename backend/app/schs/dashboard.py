from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ..core.trust.rules import Band
from .access import SessionStatus


class DashboardOverview(BaseModel):
    active_sessions: int
    pending_approvals: int


class DashboardRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DashboardSession(DashboardRow):
    id: UUID
    status: SessionStatus
    created_at: datetime
    expires_at: datetime


class DashboardCapability(DashboardRow):
    id: UUID
    session_id: UUID | None
    task_id: UUID | None
    action: str
    resource_id: str
    expires_at: datetime | None
    revoked_at: datetime | None


class DashboardTask(DashboardRow):
    id: UUID
    title: str
    status: str


class TrustSummary(BaseModel):
    agent_id: UUID
    score: int
    score_persisted: bool
    band: Band
    active_sessions: int


class TrustAdjustment(DashboardRow):
    id: UUID
    created_at: datetime
    delta: int
    reason_code: str
    previous_score: int | None
    new_score: int | None
    rule: str | None


class TrustRestrictions(BaseModel):
    mode: Literal["none", "allowlist", "blocked"]
    allowed_actions: list[str]


class DashboardTrust(BaseModel):
    score: int
    score_persisted: bool
    band: Band
    history: list[TrustAdjustment]
    restrictions: TrustRestrictions


class DashboardAgent(BaseModel):
    sessions: list[DashboardSession]
    capabilities: list[DashboardCapability]
    tasks: list[DashboardTask]
    trust: DashboardTrust


class DashboardIntegration(BaseModel):
    id: Literal["browser", "mcp", "local"]
    name: str
    status: Literal["configured", "enabled", "disabled"]
    connection_status: Literal["unknown"] = "unknown"
    operations: list[str]
    detail: str
