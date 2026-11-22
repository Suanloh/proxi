from typing import Protocol, TypeVar
from uuid import UUID

from ..models.records import Record

T = TypeVar("T", bound=Record)


class RecordRepository(Protocol[T]):
    def add(self, record: T) -> T: ...
    def get(self, record_id: UUID) -> T | None: ...


class MutableRecordRepository(RecordRepository[T], Protocol[T]):
    def update(self, record: T) -> T: ...
