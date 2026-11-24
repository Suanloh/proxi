from enum import StrEnum
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict

from .authz import ActionRequest, Reason


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class ApprovalSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    request: ActionRequest
    capability_id: UUID
    policy_version_ids: tuple[UUID, ...]


class ApprovalDetails(BaseModel):
    id: UUID
    request: ActionRequest
    reason: Reason
    status: ApprovalStatus
    policy_version_ids: tuple[UUID, ...]
    expires_at: AwareDatetime
    created_at: AwareDatetime
    reviewed_by: UUID | None
    reviewed_at: AwareDatetime | None
    review_outcome: ApprovalStatus | None
    consumed_at: AwareDatetime | None
