from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4


@dataclass(kw_only=True)
class Record:
    id: UUID = field(default_factory=uuid4)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(kw_only=True)
class User(Record):
    email: str
    status: str = "active"


class AgentType(StrEnum):
    BROWSER = "browser"
    MCP = "mcp"
    LOCAL = "local"
    CODING = "coding"


class AgentStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


@dataclass(kw_only=True)
class Agent(Record):
    owner_id: UUID
    name: str
    status: AgentStatus = AgentStatus.ACTIVE
    type: AgentType | None = None
    description: str | None = None
    last_seen_at: datetime | None = None

    def __post_init__(self) -> None:
        self.status = AgentStatus(self.status)
        if self.type is not None:
            self.type = AgentType(self.type)


@dataclass(kw_only=True)
class AgentSession(Record):
    agent_id: UUID
    expires_at: datetime
    revoked_at: datetime | None = None


@dataclass(kw_only=True)
class Credential(Record):
    agent_id: UUID
    secret_ref: str
    expires_at: datetime | None = None
    revoked_at: datetime | None = None


@dataclass(kw_only=True)
class Capability(Record):
    agent_id: UUID
    action: str
    resource: str
    expires_at: datetime | None = None
    revoked_at: datetime | None = None


@dataclass(kw_only=True)
class Task(Record):
    agent_id: UUID
    objective: str
    status: str = "pending"


@dataclass(kw_only=True)
class IntentInterpretation(Record):
    task_id: UUID
    interpreter: str
    summary: str
    status: str = "proposed"


@dataclass(kw_only=True)
class Policy(Record):
    owner_id: UUID
    name: str
    status: str = "active"


@dataclass(kw_only=True)
class PolicyVersion(Record):
    policy_id: UUID
    version: int
    status: str = "draft"
    superseded_at: datetime | None = None


@dataclass(kw_only=True)
class PolicyRule(Record):
    policy_version_id: UUID
    position: int
    action: str
    resource: str
    outcome: str


@dataclass(kw_only=True)
class ActionRequest(Record):
    session_id: UUID
    action: str
    resource: str
    task_id: UUID | None = None


@dataclass(kw_only=True)
class AuthorizationDecision(Record):
    action_request_id: UUID
    outcome: str
    reason_code: str
    policy_version_id: UUID | None = None


@dataclass(kw_only=True)
class ApprovalRequest(Record):
    decision_id: UUID
    expires_at: datetime


@dataclass(kw_only=True)
class ApprovalRecord(Record):
    approval_request_id: UUID
    reviewer_id: UUID
    outcome: str


@dataclass(kw_only=True)
class BehaviourEvent(Record):
    agent_id: UUID
    event_type: str


@dataclass(kw_only=True)
class TrustScore(Record):
    agent_id: UUID
    score: int


@dataclass(kw_only=True)
class TrustEvent(Record):
    agent_id: UUID
    delta: int
    reason_code: str


@dataclass(kw_only=True)
class AuditLog(Record):
    event_type: str
    agent_id: UUID | None = None
    action_request_id: UUID | None = None


@dataclass(kw_only=True)
class SecurityEvent(Record):
    event_type: str
    severity: str
    agent_id: UUID | None = None


@dataclass(kw_only=True)
class IntegrationConnection(Record):
    agent_id: UUID
    kind: str
    name: str
    status: str = "disabled"
