from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..core.events import EventType
from ..infra.db.models import (
    ActionRequestRow, AgentRow, ApprovalRecordRow, ApprovalRequestRow, AuditLogRow,
    AuthorizationDecisionRow, CapabilityRow, SecurityEventRow, TaskRow,
)
from ..schs.browser_experience import BrowserEvent, CapabilityScope, PendingApproval

_ACTION_EVENTS = (EventType.ACTION_ALLOWED, EventType.ACTION_HELD, EventType.ACTION_BLOCKED,
                  EventType.ACTION_EXECUTED, EventType.AUTHENTICATION_DENIED, EventType.CAPABILITY_REVOKED,
                  EventType.SESSION_REVOKED, EventType.APPROVAL_GRANTED, EventType.APPROVAL_REJECTED,
                  EventType.APPROVAL_CANCELLED)


def browser_events(db: Session, owner: UUID, session_id: UUID | None = None) -> list[BrowserEvent]:
    results = []
    for row in (AuditLogRow, SecurityEventRow):
        query = (select(row.event_type, row.action, row.outcome, row.reason, row.created_at)
                 .join(AgentRow, AgentRow.id == row.agent_id)
                 .where(row.owner_id == owner, AgentRow.owner_id == owner, AgentRow.type == "browser",
                        row.correlation_id.is_not(None)))
        if row is AuditLogRow:
            query = query.where(row.event_type.in_(_ACTION_EVENTS))
        query = query.where(or_(row.action.startswith("browser."), row.action.is_(None)))
        if session_id is not None:
            query = query.where(row.session_id == session_id)
        for entry in db.execute(query.order_by(row.created_at.desc(), row.id.desc()).limit(20)):
            results.append(BrowserEvent.model_validate(entry, from_attributes=True))
    return sorted(results, key=lambda event: event.created_at, reverse=True)[:20]


def task_scope(db: Session, owner: UUID, agent_id: UUID, session_id: UUID, task: TaskRow):
    now = datetime.now(UTC)
    capabilities = db.scalars(select(CapabilityRow).where(
        CapabilityRow.agent_id == agent_id, CapabilityRow.session_id == session_id,
        CapabilityRow.task_id == task.id, CapabilityRow.action.startswith("browser."),
        CapabilityRow.revoked_at.is_(None), CapabilityRow.expires_at > now,
    ).order_by(CapabilityRow.created_at.desc(), CapabilityRow.id.desc()).limit(50))
    pending = db.execute(select(ApprovalRequestRow.id, ActionRequestRow.action, ApprovalRequestRow.expires_at)
        .join(AuthorizationDecisionRow, AuthorizationDecisionRow.id == ApprovalRequestRow.decision_id)
        .join(ActionRequestRow, ActionRequestRow.id == AuthorizationDecisionRow.action_request_id)
        .outerjoin(ApprovalRecordRow, ApprovalRecordRow.approval_request_id == ApprovalRequestRow.id)
        .where(ApprovalRequestRow.reviewer_id == owner, ApprovalRequestRow.expires_at > now,
               ApprovalRequestRow.consumed_at.is_(None), ApprovalRecordRow.id.is_(None),
               ActionRequestRow.session_id == session_id, ActionRequestRow.task_id == task.id,
               ActionRequestRow.action.startswith("browser."))
        .order_by(ApprovalRequestRow.created_at.desc(), ApprovalRequestRow.id.desc()).limit(20))
    return ([CapabilityScope.model_validate(cap, from_attributes=True) for cap in capabilities],
            [PendingApproval.model_validate(item, from_attributes=True) for item in pending])
