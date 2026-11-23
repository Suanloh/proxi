from collections.abc import Callable, Iterable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from pydantic import ValidationError

from ..core.behaviour.rules import DENIAL_REASONS, Finding, Rule, denial
from ..core.identity.lifecycle import require_active
from ..core.repositories import RecordRepository
from ..core.trust.rules import Band, TrustRules, bounded_score
from ..models.records import BehaviourEvent, IntentInterpretation, TrustEvent, TrustScore
from ..schs.authz import ActionRequest, ContextAttributes, Reason
from ..schs.intent import IntentProposal
from .identity import AgentIdentityService


class TrustHistory(Protocol):
    def score(self, agent_id: UUID) -> TrustScore | None: ...
    def save(self, score: TrustScore) -> TrustScore: ...
    def observe(self, event: BehaviourEvent) -> None: ...
    def adjust(self, event: TrustEvent) -> None: ...
    def seen(self, request: ActionRequest, rules: Iterable[Rule]) -> bool: ...
    def last_action(self, request: ActionRequest) -> str | None: ...
    def recent_count(self, agent_id: UUID, reasons: Iterable[str], since: datetime, limit: int) -> int: ...


class TrustReviewConflict(ValueError):
    pass


class DynamicTrust:
    """All operations run in a transaction under the agent's existing row lock."""

    def __init__(self, history: TrustHistory, intents: RecordRepository[IntentInterpretation], rules: TrustRules,
                 *, clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self._history = history
        self._intents = intents
        self._rules = rules
        self._clock = clock

    def _score(self, agent_id: UUID) -> TrustScore:
        return self._history.score(agent_id) or TrustScore(agent_id=agent_id, score=self._rules.initial_score)

    def allows(self, request: ActionRequest, attributes: ContextAttributes) -> bool:
        band = self._rules.band(self._score(request.agent_id).score)
        return band in {Band.NORMAL, Band.MONITORED} or (
            band == Band.RESTRICTED and request.action in self._rules.restricted_actions
        )

    def _emit(self, score: TrustScore, finding: Finding, now: datetime, request: ActionRequest | None = None,
              *, reviewer_id: UUID | None = None, delta: int = 0, violation: bool = False,
              compliant_count: int | None = None) -> TrustScore:
        event = BehaviourEvent(
            agent_id=score.agent_id, observed_at=now, event_type=finding.rule, reason_code=finding.reason,
            band=self._rules.band(score.score), request_id=request.request_id if request else None,
            session_id=request.session_id if request else None, task_id=request.task_id if request else None,
            action=request.action if request else None, reviewer_id=reviewer_id,
        )
        self._history.observe(event)
        updated = replace(score, score=bounded_score(score.score, delta),
                          last_violation_at=now if violation else score.last_violation_at,
                          compliant_count=0 if violation else (score.compliant_count if compliant_count is None
                                                               else compliant_count))
        if updated.score != score.score:
            updated.last_adjusted_at = now
            self._history.adjust(TrustEvent(agent_id=score.agent_id, behaviour_event_id=event.id,
                                            previous_score=score.score, new_score=updated.score,
                                            delta=updated.score - score.score, reason_code=finding.reason,
                                            rule=finding.rule))
        if updated != score or score.created_at is None:
            return self._history.save(updated)
        return updated

    def _record(self, request: ActionRequest, finding: Finding, *, violation: bool = False) -> None:
        self._emit(self._score(request.agent_id), finding, self._clock(), request,
                   delta=self._rules.weights.for_rule(finding.rule), violation=violation)

    def blocked(self, request: ActionRequest, reason: Reason) -> None:
        finding = denial(reason)
        if finding is None:
            return
        violation = reason in DENIAL_REASONS
        if violation and self._repeated(request, DENIAL_REASONS, self._rules.denied_threshold):
            finding = Finding(Rule.REPEATED_DENIED, reason)
        self._record(request, finding, violation=violation)

    def _repeated(self, request: ActionRequest, reasons: Iterable[str], threshold: int) -> bool:
        cutoff = self._clock() - timedelta(seconds=self._rules.repeat_window_seconds)
        return self._history.recent_count(request.agent_id, reasons, cutoff, threshold - 1) >= threshold - 1

    def session_anomaly(self, request: ActionRequest, reason: Reason) -> None:
        self._record(request, Finding(Rule.SESSION, reason))

    def approval_created(self, request: ActionRequest) -> None:
        reason = Reason.APPROVAL_REQUIRED
        repeated = self._repeated(request, (reason,), self._rules.approval_threshold)
        self._record(request, Finding(Rule.REPEATED_APPROVAL if repeated else Rule.APPROVAL, reason), violation=repeated)

    def inspect_grant(self, request: ActionRequest, proposal_ids: Iterable[UUID]) -> None:
        if self._outside_intent(request, proposal_ids):
            self._record(request, Finding(Rule.UNUSUAL, "outside_original_proposal"), violation=True)
        predecessors = self._rules.predecessors.get(request.action)
        if predecessors and self._history.last_action(request) not in predecessors:
            self._record(request, Finding(Rule.SEQUENCE, "expected_predecessor_missing"), violation=True)

    def _outside_intent(self, request: ActionRequest, proposal_ids: Iterable[UUID]) -> bool:
        comparable = False
        for proposal_id in set(proposal_ids):
            source = self._intents.get(proposal_id)
            if source is None or source.status != "proposed" or source.task_id != request.task_id or source.proposal is None:
                return False
            try:
                baseline = IntentProposal.model_validate(source.proposal).proposed_permissions
            except ValidationError:
                return False
            if (request.action in baseline.allowed_actions + baseline.approval_required_actions
                    and request.resource in baseline.resource_scope):
                return False
            comparable = True
        return comparable

    def authorized(self, request: ActionRequest) -> None:
        self._record(request, Finding(Rule.NORMAL, Reason.CHECKS_PASSED))

    def execution(self, request: ActionRequest, *, succeeded: bool) -> None:
        if not succeeded:
            self._emit(self._score(request.agent_id), Finding(Rule.EXECUTION_FAILED, "adapter_failed"),
                       self._clock(), request, compliant_count=0)
            return
        clean = not self._history.seen(request, (Rule.EXECUTED, Rule.SEQUENCE, Rule.UNUSUAL))
        now = self._clock()
        score = self._score(request.agent_id)
        count = score.compliant_count
        if clean and score.score < 100:
            count = min(count + 1, self._rules.recovery_successes)
        updated = self._emit(score, Finding(Rule.EXECUTED, "adapter_succeeded"), now, request, compliant_count=count)
        if clean and count >= self._rules.recovery_successes and self._cooled_down(updated, now):
            finding = Finding(Rule.RECOVERY, "compliant_execution_streak")
            self._emit(updated, finding, now, request, delta=self._rules.weights.for_rule(finding.rule), compliant_count=0)

    def _cooled_down(self, score: TrustScore, now: datetime) -> bool:
        cutoff = now - timedelta(seconds=self._rules.recovery_cooldown_seconds)
        return all(value is None or value <= cutoff for value in (score.last_adjusted_at, score.last_violation_at))

    def review(self, identity: AgentIdentityService, owner_id: UUID, agent_id: UUID) -> TrustScore:
        identity.require_active_owner(owner_id)
        agent = identity.get_owned(owner_id, agent_id, for_update=True)
        require_active(agent.status)
        score = self._score(agent.id)
        band = self._rules.band(score.score)
        now = self._clock()
        if band not in {Band.SUSPENDED, Band.RESTRICTED} or not self._cooled_down(score, now):
            raise TrustReviewConflict
        target = self._rules.restricted_min if band == Band.SUSPENDED else self._rules.monitored_min
        return self._emit(score, Finding(Rule.REVIEW, "owner_authorized_limited_recovery"), now,
                          reviewer_id=owner_id, delta=target - score.score, compliant_count=0)
