from typing import Protocol, TypeVar
from uuid import UUID

from ..models.records import Agent, Record

T = TypeVar("T", bound=Record)


class RecordRepository(Protocol[T]):
    def add(self, record: T) -> T: ...
    def get(self, record_id: UUID) -> T | None: ...


class MutableRecordRepository(RecordRepository[T], Protocol[T]):
    def update(self, record: T) -> T: ...


class AgentConflict(ValueError):
    pass


class AgentRepository(MutableRecordRepository[Agent], Protocol):
    def get_for_update(self, agent_id: UUID) -> Agent | None: ...
    def list_owned(self, owner_id: UUID) -> list[Agent]: ...
    def get_owned(self, owner_id: UUID, agent_id: UUID, *, for_update: bool = False) -> Agent | None: ...
