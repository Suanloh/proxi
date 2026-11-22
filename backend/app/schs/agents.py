from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints, model_validator

from ..models.records import AgentStatus, AgentType


def validate_text(value: str) -> str:
    if "\x00" in value or any("\ud800" <= char <= "\udfff" for char in value):
        raise ValueError("Invalid text")
    return value


AgentName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120),
                      AfterValidator(validate_text)]
AgentDescription = Annotated[str, StringConstraints(max_length=2000), AfterValidator(validate_text)]


class AgentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: AgentName
    type: AgentType
    description: AgentDescription | None = None


class AgentPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: AgentName | None = None
    type: AgentType | None = None
    description: AgentDescription | None = None
    status: AgentStatus | None = None

    @model_validator(mode="after")
    def check_changes(self) -> Self:
        if not self.model_fields_set or any(
            getattr(self, field) is None for field in self.model_fields_set - {"description"}
        ):
            raise ValueError("Provide at least one change; only description may be null")
        return self

class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    type: AgentType | None
    description: str | None
    status: AgentStatus
    created_at: datetime
    last_seen_at: datetime | None
