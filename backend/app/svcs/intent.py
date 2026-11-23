import json
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from ..core.events import EventType
from ..core.identity.lifecycle import require_active
from ..core.repositories import RecordRepository
from ..models.records import IntentInterpretation as IntentRecord, Task
from ..schs.intent import IntentInterpretation, IntentProposal, IntentProposalResponse
from .identity import AgentIdentityService


class IntentFailureCode(StrEnum):
    NOT_CONFIGURED = "not_configured"
    PROVIDER_ERROR = "provider_error"
    TIMEOUT = "timeout"
    INVALID_OUTPUT = "invalid_output"


class IntentFailure(Exception):
    def __init__(self, code: IntentFailureCode) -> None:
        super().__init__(code.value)
        self.code = code


class IntentProvider(Protocol):
    @property
    def name(self) -> str: ...
    async def suggest(self, task: str) -> str: ...


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


class IntentInterpreter:
    def __init__(self, provider: IntentProvider) -> None:
        self._provider = provider

    @property
    def name(self) -> str:
        return self._provider.name

    async def interpret(self, task: str) -> IntentProposal:
        raw = await self._provider.suggest(task)
        try:
            data = json.loads(raw, object_pairs_hook=_unique_keys)
            interpretation = IntentInterpretation.model_validate(data)
        except (ValueError, RecursionError):
            raise IntentFailure(IntentFailureCode.INVALID_OUTPUT) from None
        return IntentProposal(interpretation=interpretation, proposed_permissions=interpretation.permissions())


class IntentReview:
    def __init__(
        self, identity: AgentIdentityService, tasks: RecordRepository[Task], records: RecordRepository[IntentRecord],
    ) -> None:
        self._identity = identity
        self._tasks = tasks
        self._records = records

    def require_active_agent(self, owner: UUID, agent_id: UUID, *, for_update: bool = False) -> None:
        self._identity.require_active_owner(owner)
        require_active(self._identity.get_owned(owner, agent_id, for_update=for_update).status)

    def record_proposal(
        self, owner: UUID, agent_id: UUID, task: str, interpreter: str, proposal: IntentProposal,
    ) -> IntentProposalResponse:
        self.require_active_agent(owner, agent_id, for_update=True)
        stored_task = self._tasks.add(Task(agent_id=agent_id, objective=task))
        stored = self._records.add(IntentRecord(
            task_id=stored_task.id, interpreter=interpreter, summary=proposal.interpretation.task_objective,
            proposal=proposal.model_dump(mode="json"),
        ))
        return self._response(stored, proposal)

    def record_failure(
        self, owner: UUID, agent_id: UUID, task: str, interpreter: str, failure: IntentFailureCode,
    ) -> None:
        self.require_active_agent(owner, agent_id, for_update=True)
        stored_task = self._tasks.add(Task(agent_id=agent_id, objective=task))
        failure_record = self._records.add(IntentRecord(
            task_id=stored_task.id, interpreter=interpreter, summary="No permission proposal was generated",
            status="failed", failure_code=failure.value,
        ))

        self._identity.events.owner(EventType.INTEGRATION_ERROR, owner, agent_id, resource_id=failure_record.id,
                                    outcome="failed", reason=failure.value)

    def get_proposal(self, owner: UUID, agent_id: UUID, interpretation_id: UUID) -> IntentProposalResponse | None:
        self._identity.require_active_owner(owner)
        self._identity.get_owned(owner, agent_id)
        stored = self._records.get(interpretation_id)
        if stored is None or stored.status != "proposed" or stored.proposal is None:
            return None
        task = self._tasks.get(stored.task_id)
        if task is None or task.agent_id != agent_id:
            return None
        return self._response(stored, IntentProposal.model_validate(stored.proposal))

    @staticmethod
    def _response(stored: IntentRecord, proposal: IntentProposal) -> IntentProposalResponse:
        if stored.created_at is None:
            raise RuntimeError("Missing persisted proposal timestamp")
        return IntentProposalResponse(
            id=stored.id, task_id=stored.task_id, created_at=stored.created_at,
            interpretation=proposal.interpretation, proposed_permissions=proposal.proposed_permissions,
        )
