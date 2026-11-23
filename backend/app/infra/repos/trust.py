from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.behaviour.rules import Rule
from ...models.records import BehaviourEvent, TrustEvent, TrustScore
from ...schs.authz import ActionRequest
from ..db.models import BehaviourEventRow, TrustScoreRow
from .sqlalchemy import mutable_repository, repository


class SqlTrustHistory:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._scores = mutable_repository(session, TrustScore)
        self._behaviour = repository(session, BehaviourEvent)
        self._adjustments = repository(session, TrustEvent)

    def score(self, agent_id: UUID) -> TrustScore | None:
        score_id = self._session.scalar(select(TrustScoreRow.id).where(TrustScoreRow.agent_id == agent_id))
        return self._scores.get(score_id) if score_id is not None else None

    def save(self, score: TrustScore) -> TrustScore:
        if score.created_at is None:
            return self._scores.add(score)
        return self._scores.update(score)

    def observe(self, event: BehaviourEvent) -> None:
        self._behaviour.add(event)

    def adjust(self, event: TrustEvent) -> None:
        self._adjustments.add(event)

    def seen(self, request: ActionRequest, rules: Iterable[Rule]) -> bool:
        row = BehaviourEventRow
        return self._session.scalar(select(row.id).where(
            row.agent_id == request.agent_id, row.request_id == request.request_id,
            row.event_type.in_(tuple(rules)),
        ).limit(1)) is not None

    def last_action(self, request: ActionRequest) -> str | None:
        row = BehaviourEventRow
        return self._session.scalar(select(row.action).where(
            row.agent_id == request.agent_id, row.session_id == request.session_id,
            row.task_id == request.task_id, row.event_type == Rule.EXECUTED,
        ).order_by(row.observed_at.desc(), row.id.desc()).limit(1))

    def recent_count(self, agent_id: UUID, reasons: Iterable[str], since: datetime, limit: int) -> int:
        row = BehaviourEventRow
        return len(self._session.scalars(select(row.id).where(
            row.agent_id == agent_id, row.reason_code.in_(tuple(reasons)), row.observed_at >= since,
        ).limit(limit)).all())
