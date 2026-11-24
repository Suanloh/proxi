import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from pydantic import ValidationError

from ..core.events import EventType
from ..core.repositories import ApprovalEntry, ApprovalRepository
from ..models.records import ApprovalRecord, ApprovalRequest, AuthorizationDecision
from ..schs.approvals import ApprovalDetails, ApprovalSnapshot, ApprovalStatus
from ..schs.authz import ActionRequest, Decision, Outcome, Reason
from .identity import AgentIdentityService
from .policy_checks import PolicyRetrieval


class ApprovalNotFound(LookupError):
    pass


class ApprovalConflict(ValueError):
    pass


@dataclass(frozen=True)
class ApprovalClaim:
    reviewer_id: UUID
    policy_version_ids: tuple[UUID, ...]
    expires_at: datetime


def invalid_approval(decision: Decision) -> Decision:
    return Decision(request_id=decision.request_id, outcome=Outcome.BLOCK, reason=Reason.APPROVAL_INVALID,
                    failed_checks=(Reason.APPROVAL_INVALID,), matched_policy=decision.matched_policy)


def review_outcome(review: ApprovalRecord | None) -> ApprovalStatus | None:
    return ApprovalStatus(review.outcome.upper()) if review is not None else None


def status(entry: ApprovalEntry, now: datetime) -> ApprovalStatus:
    approval, _, review = entry
    outcome = review_outcome(review) or ApprovalStatus.PENDING
    if (outcome in {ApprovalStatus.PENDING, ApprovalStatus.APPROVED}
            and approval.consumed_at is None and now >= approval.expires_at):
        return ApprovalStatus.EXPIRED
    return outcome


def details(entry: ApprovalEntry, now: datetime) -> ApprovalDetails:
    approval, decision, review = entry
    snapshot = ApprovalSnapshot.model_validate(approval.snapshot)
    return ApprovalDetails.model_validate({
        "id": approval.id, "request": snapshot.request, "reason": decision.reason_code,
        "status": status(entry, now), "policy_version_ids": snapshot.policy_version_ids,
        "expires_at": approval.expires_at, "created_at": approval.created_at,
        "reviewed_by": review.reviewer_id if review else None, "reviewed_at": review.created_at if review else None,
        "review_outcome": review_outcome(review), "consumed_at": approval.consumed_at,
    })


class ActionApprovals:
    def __init__(self, approvals: ApprovalRepository, identity: AgentIdentityService, policies: PolicyRetrieval,
                 *, clock: Callable[[], datetime] = lambda: datetime.now(UTC),
                 on_created: Callable[[ActionRequest], None] | None = None) -> None:
        self._on_created = on_created
        self._approvals = approvals
        self._identity = identity
        self._policies = policies
        self._clock = clock

    def prepare(self, request: ActionRequest, capability_id: UUID | None, decision: Decision,
                *, claim: bool) -> tuple[Decision, UUID | None, ApprovalClaim | None]:
        if decision.outcome == Outcome.BLOCK:
            return decision, None, None
        entry = self._approvals.get(request.request_id, for_update=True)
        info, policy = decision.required_approval, decision.matched_policy
        now = self._clock()
        if decision.outcome == Outcome.HOLD and capability_id is not None and info is not None and policy is not None:
            snapshot = ApprovalSnapshot(request=request, capability_id=capability_id,
                                        policy_version_ids=info.policy_version_ids).model_dump(mode="json")
            if entry is None:
                persisted = AuthorizationDecision(action_request_id=request.request_id, outcome=Outcome.HOLD,
                                                  reason_code=decision.reason, policy_version_id=policy.version_id)
                approval = ApprovalRequest(id=request.request_id, decision_id=persisted.id, snapshot=snapshot,
                                           reviewer_id=info.reviewer_id, expires_at=now + timedelta(minutes=5))
                if not self._approvals.add(approval, persisted):
                    return invalid_approval(decision), None, None
                if self._on_created is not None:
                    self._on_created(request)
                return decision, request.request_id, None
            approval, original, _ = entry
            if (approval.reviewer_id == info.reviewer_id and original.outcome == Outcome.HOLD
                    and original.policy_version_id == policy.version_id
                    and json.dumps(approval.snapshot, sort_keys=True) == json.dumps(snapshot, sort_keys=True)):
                current = status(entry, now)
                if current == ApprovalStatus.PENDING:
                    return decision, approval.id, None
                if current == ApprovalStatus.APPROVED and approval.consumed_at is None:
                    if claim:
                        self._approvals.consume(approval.id, now)
                        return decision, approval.id, ApprovalClaim(info.reviewer_id, info.policy_version_ids,
                                                                    approval.expires_at)
                    return decision, approval.id, None
        elif entry is None and decision.outcome == Outcome.ALLOW:
            return decision, None, None
        return invalid_approval(decision), None, None

    def _owned(self, owner_id: UUID, approval_id: UUID, *, lock: bool = False) -> ApprovalEntry:
        entry = self._approvals.get(approval_id, for_update=lock)
        if entry is None or entry[0].reviewer_id != owner_id or entry[1].outcome != Outcome.HOLD:
            raise ApprovalNotFound
        return entry

    def list_owned(self, owner_id: UUID, *, pending: bool, limit: int, offset: int) -> list[ApprovalDetails]:
        self._identity.require_active_owner(owner_id)
        now = self._clock()
        return [details(entry, now) for entry in self._approvals.list_owned(owner_id, now, pending=pending,
                                                                          limit=limit, offset=offset)]

    def get(self, owner_id: UUID, approval_id: UUID) -> ApprovalDetails:
        self._identity.require_active_owner(owner_id)
        return details(self._owned(owner_id, approval_id), self._clock())

    def review(self, owner_id: UUID, approval_id: UUID, target: ApprovalStatus) -> ApprovalDetails:
        self._identity.require_active_owner(owner_id)
        initial = self._owned(owner_id, approval_id)
        snapshot = ApprovalSnapshot.model_validate(initial[0].snapshot)
        agent = self._identity.get_owned(owner_id, snapshot.request.agent_id, for_update=True)
        entry = self._owned(owner_id, approval_id, lock=True)
        now = self._clock()
        current = status(entry, now)
        if target not in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.CANCELLED}:
            raise ApprovalConflict
        if current == target:
            return details(entry, now)
        if current != ApprovalStatus.PENDING:
            raise ApprovalConflict
        if target == ApprovalStatus.APPROVED:
            try:
                policies = self._policies.active(agent, snapshot.request.task_id, now)
            except ValidationError:
                raise ApprovalConflict from None
            if (not set(snapshot.policy_version_ids).issubset(policy.match.version_id for policy in policies)
                    or any(snapshot.request.action in policy.definition.denied_actions for policy in policies)):
                raise ApprovalConflict
        approval, decision, _ = entry
        reviewed = self._approvals.review(ApprovalRecord(approval_request_id=approval.id, reviewer_id=owner_id,
                                                         outcome=target.value.lower()))
        kind = {ApprovalStatus.APPROVED: EventType.APPROVAL_GRANTED, ApprovalStatus.REJECTED: EventType.APPROVAL_REJECTED,
                ApprovalStatus.CANCELLED: EventType.APPROVAL_CANCELLED}[target]
        self._identity.events.owner(kind, owner_id, agent.id, resource_id=approval.id,
                                    session_id=snapshot.request.session_id, request_id=snapshot.request.request_id,
                                    action=snapshot.request.action, outcome=target.value.lower())
        return details((approval, decision, reviewed), now)
