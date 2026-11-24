from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict

from .authz import Decision
from .intent import ShortText


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    request_id: UUID
    agent_id: UUID
    session_id: UUID
    task_id: UUID | None = None
    capability_id: UUID | None = None
    timestamp: AwareDatetime
    resource: ShortText


class CatalogResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entry: Literal["proxi"]
    category: Literal["demo"]


class ToolResponse(BaseModel):
    decision: Decision
    executed: bool
    approval_id: UUID | None = None
    result: CatalogResult | None = None
