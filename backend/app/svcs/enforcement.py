from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from inspect import isasyncgenfunction, iscoroutinefunction, isgeneratorfunction
from typing import Generic, TypeVar
from uuid import UUID

from ..models.records import AgentType
from ..schs.authz import ActionRequest, ContextAttributes, Decision, Outcome, Reason
from .authz import AuthorizationEngine

T = TypeVar("T")
AuthorizationTransaction = Callable[[], AbstractContextManager[AuthorizationEngine]]


@dataclass(frozen=True)
class EnforcementResult(Generic[T]):
    decision: Decision
    executed: bool = False
    result: T | None = None


class EnforcementController(Generic[T]):
    def __init__(
        self, transaction: AuthorizationTransaction, record_decision: Callable[[Decision], None],
        adapters: Mapping[tuple[AgentType, str], Callable[[ActionRequest], T]],
    ) -> None:
        self._transaction = transaction
        self._record = record_decision
        self._adapters = dict(adapters)
        for adapter in self._adapters.values():
            for target in (adapter, getattr(adapter, "__call__", None)):
                if iscoroutinefunction(target) or isasyncgenfunction(target) or isgeneratorfunction(target):
                    raise TypeError("Execution adapters must run synchronously without deferring work")

    def enforce(
        self, request: ActionRequest, token: str, capability_id: UUID | None,
        *, trusted_context: Callable[[], ContextAttributes] | None = None,
    ) -> EnforcementResult[T]:
        snapshot = request.model_copy(deep=True)
        with self._transaction() as engine:
            decision = engine.evaluate(snapshot, token, capability_id,
                                       trusted_context=trusted_context() if trusted_context else None)
        if decision.outcome != Outcome.ALLOW:
            self._record(decision)
            return EnforcementResult(decision)
        adapter = self._adapters.get((snapshot.integration_type, snapshot.action))
        if adapter is None:
            decision = Decision(request_id=snapshot.request_id, outcome=Outcome.BLOCK,
                                reason=Reason.ADAPTER_UNAVAILABLE, failed_checks=(Reason.ADAPTER_UNAVAILABLE,),
                                matched_policy=decision.matched_policy)
            self._record(decision)
            return EnforcementResult(decision)

        # Keep the agent lock through synchronous dispatch; revocations use the same lock.
        with self._transaction() as engine:
            decision = engine.evaluate(snapshot, token, capability_id,
                                       trusted_context=trusted_context() if trusted_context else None)
            self._record(decision)
            if decision.outcome != Outcome.ALLOW:
                return EnforcementResult(decision)
            return EnforcementResult(decision, executed=True, result=adapter(snapshot))
