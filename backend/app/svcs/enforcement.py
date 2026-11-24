from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from inspect import isasyncgenfunction, iscoroutinefunction, isgeneratorfunction
from typing import Generic, TypeVar
from uuid import UUID

from ..core.events import enforcement_correlation
from ..models.records import AgentType
from ..schs.authz import ActionRequest, ContextAttributes, Decision, Outcome, Reason
from .approvals import invalid_approval
from .authz import AuthorizationEngine

T = TypeVar("T")
AuthorizationTransaction = Callable[[], AbstractContextManager[AuthorizationEngine]]


@dataclass(frozen=True)
class EnforcementResult(Generic[T]):
    decision: Decision
    executed: bool = False
    result: T | None = None
    approval_id: UUID | None = None


class EnforcementController(Generic[T]):
    def __init__(
        self, transaction: AuthorizationTransaction, record_decision: Callable[[Decision], None],
        adapters: Mapping[tuple[AgentType, str], Callable[[ActionRequest], T]],
        *, restriction: Callable[[ActionRequest], Reason | None] | None = None,
    ) -> None:
        self._transaction = transaction
        self._restriction = restriction
        self._record = record_decision
        self._adapters = dict(adapters)
        for adapter in self._adapters.values():
            for target in (adapter, getattr(adapter, "__call__", None)):
                if iscoroutinefunction(target) or isasyncgenfunction(target) or isgeneratorfunction(target):
                    raise TypeError("Execution adapters must run synchronously without deferring work")

    def _restrict(self, request: ActionRequest, decision: Decision) -> Decision:
        if decision.outcome == Outcome.BLOCK or self._restriction is None:
            return decision
        reason = self._restriction(request.model_copy(deep=True))
        if reason is None:
            return decision
        return Decision(request_id=request.request_id, outcome=Outcome.BLOCK, reason=reason,
                        failed_checks=(reason,), matched_policy=decision.matched_policy)

    @enforcement_correlation()
    def enforce(
        self, request: ActionRequest, token: str, capability_id: UUID | None,
        *, trusted_context: Callable[[], ContextAttributes] | None = None,
    ) -> EnforcementResult[T]:
        snapshot = request.model_copy(deep=True)
        adapter = self._adapters.get((snapshot.integration_type, snapshot.action))
        with self._transaction() as engine:
            context = trusted_context() if trusted_context else None
            decision = engine.evaluate(snapshot, token, capability_id, trusted_context=context, _audit=False)
            decision = self._restrict(snapshot, decision)
            if engine.approvals is None:
                raise RuntimeError("Enforcement requires an approval repository")
            decision, approval_id, claim = engine.approvals.prepare(snapshot, capability_id, decision,
                                                                   claim=adapter is not None)
            finished = claim is None and decision.outcome != Outcome.ALLOW
            if not finished and adapter is None:
                decision = Decision(request_id=snapshot.request_id, outcome=Outcome.BLOCK,
                                    reason=Reason.ADAPTER_UNAVAILABLE, failed_checks=(Reason.ADAPTER_UNAVAILABLE,),
                                    matched_policy=decision.matched_policy)
                finished = True
            if finished:
                engine.record_decision(snapshot, token, decision)
        if finished:
            self._record(decision)
            return EnforcementResult(decision, approval_id=approval_id)
        assert adapter is not None

        # Commit the claim first so a crash or an adapter failure cannot make it reusable.
        # Keep the agent lock through dispatch; revocations use the same lock.
        failure: Exception | None = None
        with self._transaction() as engine:
            context = trusted_context() if trusted_context else None
            decision = engine.evaluate(snapshot, token, capability_id, trusted_context=context, _claim=claim,
                                       _dispatch=True, _audit=False)
            decision = self._restrict(snapshot, decision)
            if claim is None:
                if engine.approvals is None:
                    raise RuntimeError("Enforcement requires an approval repository")
                decision, approval_id, _ = engine.approvals.prepare(snapshot, capability_id, decision, claim=False)
            self._record(decision)
            if decision.outcome != Outcome.ALLOW:
                engine.record_decision(snapshot, token, decision)
                return EnforcementResult(decision, approval_id=approval_id)
            if claim is not None and datetime.now(UTC) >= claim.expires_at:
                decision = invalid_approval(decision)
                self._record(decision)
                engine.record_decision(snapshot, token, decision)
                return EnforcementResult(decision, approval_id=approval_id)
            engine.record_decision(snapshot, token, decision)
            if engine.behaviour is not None:
                engine.behaviour.authorized(snapshot)
            result = None
            try:
                result = adapter(snapshot.model_copy(deep=True))
            except Exception as exc:
                failure = exc
            if engine.behaviour is not None:
                engine.behaviour.execution(snapshot, succeeded=failure is None)
            engine.record_execution(snapshot, token, succeeded=failure is None)
        if failure is not None:
            raise failure
        return EnforcementResult(decision, executed=True, result=result, approval_id=approval_id)
