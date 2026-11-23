from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, MetaData, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SCHEMA = "proxi"


class Base(DeclarativeBase):
    metadata = MetaData(schema=SCHEMA, naming_convention={
        "pk": "pk_%(table_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
    })


class Row(Base):
    __abstract__ = True

    id: Mapped[UUID] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )


def ref(table: str) -> ForeignKey:
    return ForeignKey(f"{SCHEMA}.{table}.id", ondelete="RESTRICT")


class UserRow(Row):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("status IN ('active', 'disabled')", name="status"),)

    email: Mapped[str] = mapped_column(unique=True)
    status: Mapped[str] = mapped_column(server_default="active")


class AgentRow(Row):
    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("owner_id", "name"),
        CheckConstraint("status IN ('active', 'inactive', 'suspended', 'revoked')", name="status"),
        CheckConstraint("type IN ('browser', 'mcp', 'local', 'coding')", name="type"),
    )

    owner_id: Mapped[UUID] = mapped_column(ref("users"))
    name: Mapped[str]
    status: Mapped[str] = mapped_column(server_default="active")
    type: Mapped[str | None]
    description: Mapped[str | None]
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AgentSessionRow(Row):
    __tablename__ = "agent_sessions"
    __table_args__ = (Index("ix_agent_sessions_agent_expiry", "agent_id", "expires_at"),)

    agent_id: Mapped[UUID] = mapped_column(ref("agents"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CredentialRow(Row):
    __tablename__ = "credentials"

    agent_id: Mapped[UUID] = mapped_column(ref("agents"), index=True)
    secret_ref: Mapped[str] = mapped_column(unique=True)
    session_id: Mapped[UUID | None] = mapped_column(ref("agent_sessions"))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CapabilityRow(Row):
    __tablename__ = "capabilities"
    __table_args__ = (Index("ix_capabilities_agent_action", "agent_id", "action"),)

    agent_id: Mapped[UUID] = mapped_column(ref("agents"))
    action: Mapped[str]
    resource: Mapped[str]
    session_id: Mapped[UUID | None] = mapped_column(ref("agent_sessions"))
    task_id: Mapped[UUID | None] = mapped_column(ref("tasks"))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TaskRow(Row):
    __tablename__ = "tasks"
    __table_args__ = (CheckConstraint("status IN ('pending', 'completed', 'cancelled')", name="status"),)

    agent_id: Mapped[UUID] = mapped_column(ref("agents"), index=True)
    objective: Mapped[str]
    status: Mapped[str] = mapped_column(server_default="pending")


class IntentInterpretationRow(Row):
    __tablename__ = "intent_interpretations"
    __table_args__ = (
        CheckConstraint("status IN ('proposed', 'rejected', 'reviewed', 'failed')", name="status"),
        CheckConstraint(
            "(status = 'failed' AND proposal IS NULL AND failure_code IS NOT NULL) OR "
            "(status <> 'failed' AND failure_code IS NULL)", name="failure",
        ),
    )

    task_id: Mapped[UUID] = mapped_column(ref("tasks"), index=True)
    interpreter: Mapped[str]
    summary: Mapped[str]
    status: Mapped[str] = mapped_column(server_default="proposed")
    proposal: Mapped[dict[str, object] | None] = mapped_column(JSONB(none_as_null=True))
    failure_code: Mapped[str | None]


class PolicyRow(Row):
    __tablename__ = "policies"
    __table_args__ = (
        UniqueConstraint("owner_id", "name"),
        CheckConstraint("status IN ('active', 'disabled')", name="status"),
        CheckConstraint(
            "num_nonnulls(source_proposal_id, task_id, agent_id) IN (0, 3)", name="binding",
        ),
    )

    owner_id: Mapped[UUID] = mapped_column(ref("users"))
    name: Mapped[str]
    status: Mapped[str] = mapped_column(server_default="active")
    source_proposal_id: Mapped[UUID | None] = mapped_column(ref("intent_interpretations"))
    task_id: Mapped[UUID | None] = mapped_column(ref("tasks"))
    agent_id: Mapped[UUID | None] = mapped_column(ref("agents"))


class PolicyVersionRow(Row):
    __tablename__ = "policy_versions"
    __table_args__ = (
        UniqueConstraint("policy_id", "version"),
        CheckConstraint("version > 0", name="positive_version"),
        CheckConstraint("status IN ('draft', 'pending_approval', 'active', 'revoked', 'superseded')", name="status"),
        CheckConstraint("(status = 'superseded') = (superseded_at IS NOT NULL)", name="superseded_at"),
        CheckConstraint("(status = 'revoked') = (revoked_at IS NOT NULL)", name="revoked_at"),
        CheckConstraint(
            "definition IS NULL OR status = 'revoked' OR "
            "((status IN ('active', 'superseded')) = (approved_at IS NOT NULL))", name="approval",
        ),
        Index("uq_policy_versions_active", "policy_id", unique=True, postgresql_where=text("status = 'active'")),
        Index("uq_policy_versions_review", "policy_id", unique=True,
              postgresql_where=text("definition IS NOT NULL AND status IN ('draft', 'pending_approval')")),
    )

    policy_id: Mapped[UUID] = mapped_column(ref("policies"))
    version: Mapped[int]
    status: Mapped[str] = mapped_column(server_default="draft")
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    definition: Mapped[dict[str, object] | None] = mapped_column(JSONB(none_as_null=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PolicyRuleRow(Row):
    __tablename__ = "policy_rules"
    __table_args__ = (
        UniqueConstraint("policy_version_id", "position"),
        CheckConstraint("position >= 0", name="position"),
        CheckConstraint("outcome IN ('ALLOW', 'HOLD', 'BLOCK')", name="outcome"),
    )

    policy_version_id: Mapped[UUID] = mapped_column(ref("policy_versions"))
    position: Mapped[int]
    action: Mapped[str]
    resource: Mapped[str]
    outcome: Mapped[str]


class ActionRequestRow(Row):
    __tablename__ = "action_requests"

    session_id: Mapped[UUID] = mapped_column(ref("agent_sessions"), index=True)
    action: Mapped[str]
    resource: Mapped[str]
    task_id: Mapped[UUID | None] = mapped_column(ref("tasks"), index=True)


class AuthorizationDecisionRow(Row):
    __tablename__ = "authorization_decisions"
    __table_args__ = (CheckConstraint("outcome IN ('ALLOW', 'HOLD', 'BLOCK')", name="outcome"),)

    action_request_id: Mapped[UUID] = mapped_column(ref("action_requests"), index=True)
    outcome: Mapped[str]
    reason_code: Mapped[str]
    policy_version_id: Mapped[UUID | None] = mapped_column(ref("policy_versions"), index=True)


class ApprovalRequestRow(Row):
    __tablename__ = "approval_requests"

    decision_id: Mapped[UUID] = mapped_column(ref("authorization_decisions"), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ApprovalRecordRow(Row):
    __tablename__ = "approval_records"
    __table_args__ = (CheckConstraint("outcome IN ('approved', 'rejected')", name="outcome"),)

    approval_request_id: Mapped[UUID] = mapped_column(ref("approval_requests"), unique=True)
    reviewer_id: Mapped[UUID] = mapped_column(ref("users"), index=True)
    outcome: Mapped[str]


class BehaviourEventRow(Row):
    __tablename__ = "behaviour_events"
    __table_args__ = (Index("ix_behaviour_events_agent_time", "agent_id", "created_at"),)

    agent_id: Mapped[UUID] = mapped_column(ref("agents"))
    event_type: Mapped[str]


class TrustScoreRow(Row):
    __tablename__ = "trust_scores"
    __table_args__ = (CheckConstraint("score BETWEEN 0 AND 100", name="score"),)

    agent_id: Mapped[UUID] = mapped_column(ref("agents"), unique=True)
    score: Mapped[int]


class TrustEventRow(Row):
    __tablename__ = "trust_events"
    __table_args__ = (Index("ix_trust_events_agent_time", "agent_id", "created_at"),)

    agent_id: Mapped[UUID] = mapped_column(ref("agents"))
    delta: Mapped[int]
    reason_code: Mapped[str]


class AuditLogRow(Row):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_agent_time", "agent_id", "created_at"),)

    event_type: Mapped[str]
    agent_id: Mapped[UUID | None] = mapped_column(ref("agents"))
    action_request_id: Mapped[UUID | None] = mapped_column(ref("action_requests"), index=True)


class SecurityEventRow(Row):
    __tablename__ = "security_events"
    __table_args__ = (
        Index("ix_security_events_agent_time", "agent_id", "created_at"),
        CheckConstraint("severity IN ('info', 'warning', 'critical')", name="severity"),
    )

    event_type: Mapped[str]
    severity: Mapped[str]
    agent_id: Mapped[UUID | None] = mapped_column(ref("agents"))


class IntegrationConnectionRow(Row):
    __tablename__ = "integration_connections"
    __table_args__ = (
        UniqueConstraint("agent_id", "kind", "name"),
        CheckConstraint("status IN ('active', 'disabled', 'revoked')", name="status"),
    )

    agent_id: Mapped[UUID] = mapped_column(ref("agents"))
    kind: Mapped[str]
    name: Mapped[str]
    status: Mapped[str] = mapped_column(server_default="disabled")