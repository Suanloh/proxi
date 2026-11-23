from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, not_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ...core.repositories import ApprovalEntry, ApprovalRepository
from ...models.records import ApprovalRecord, ApprovalRequest, AuthorizationDecision
from ...schs.approvals import ApprovalSnapshot
from ..db.models import ActionRequestRow, ApprovalRecordRow, ApprovalRequestRow, AuthorizationDecisionRow
from .sqlalchemy import _Repository


class SqlApprovalRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._requests = _Repository(session, ApprovalRequest)
        self._decisions = _Repository(session, AuthorizationDecision)
        self._reviews = _Repository(session, ApprovalRecord)

    def _entry(self, request: ApprovalRequestRow, decision: AuthorizationDecisionRow,
               review: ApprovalRecordRow | None) -> ApprovalEntry:
        return self._requests._record(request), self._decisions._record(decision), (
            self._reviews._record(review) if review is not None else None
        )

    def get(self, request_id: UUID, *, for_update: bool = False) -> ApprovalEntry | None:
        # Fetch the review after taking the request lock, so a waiting reviewer sees the winner.
        row = self._session.get(ApprovalRequestRow, request_id, with_for_update=for_update, populate_existing=True)
        if row is None or row.snapshot is None:
            return None
        related = self._session.execute(select(AuthorizationDecisionRow, ApprovalRecordRow).outerjoin(
            ApprovalRecordRow, ApprovalRecordRow.approval_request_id == row.id,
        ).where(AuthorizationDecisionRow.id == row.decision_id)).one()
        return self._entry(row, related[0], related[1])

    def list_owned(self, owner_id: UUID, at: datetime, *, pending: bool, limit: int, offset: int) -> list[ApprovalEntry]:
        pending_filter = and_(ApprovalRecordRow.id.is_(None), ApprovalRequestRow.expires_at > at)
        statement = (
            select(ApprovalRequestRow, AuthorizationDecisionRow, ApprovalRecordRow)
            .join(AuthorizationDecisionRow, AuthorizationDecisionRow.id == ApprovalRequestRow.decision_id)
            .outerjoin(ApprovalRecordRow, ApprovalRecordRow.approval_request_id == ApprovalRequestRow.id)
            .where(ApprovalRequestRow.reviewer_id == owner_id, pending_filter if pending else not_(pending_filter))
            .order_by(ApprovalRequestRow.created_at.desc(), ApprovalRequestRow.id.desc()).limit(limit).offset(offset)
        )
        return [self._entry(request, decision, review) for request, decision, review in self._session.execute(statement)]

    def add(self, request: ApprovalRequest, decision: AuthorizationDecision) -> bool:
        snapshot = ApprovalSnapshot.model_validate(request.snapshot).request
        inserted = self._session.scalar(insert(ActionRequestRow).values(
            id=snapshot.request_id, session_id=snapshot.session_id, task_id=snapshot.task_id,
            action=snapshot.action, resource=snapshot.resource,
        ).on_conflict_do_nothing(index_elements=[ActionRequestRow.id]).returning(ActionRequestRow.id))
        if inserted is None:
            return False
        self._decisions.add(decision)
        self._requests.add(request)
        return True

    def review(self, record: ApprovalRecord) -> ApprovalRecord:
        return self._reviews.add(record)

    def consume(self, request_id: UUID, at: datetime) -> None:
        self._session.execute(update(ApprovalRequestRow).where(
            ApprovalRequestRow.id == request_id, ApprovalRequestRow.consumed_at.is_(None),
            ApprovalRequestRow.expires_at > at,
        ).values(consumed_at=at).returning(ApprovalRequestRow.id)).scalar_one()


def approval_repository(session: Session) -> ApprovalRepository:
    return SqlApprovalRepository(session)
