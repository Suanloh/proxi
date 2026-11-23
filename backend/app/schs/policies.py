from datetime import datetime, timezone
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

from ..core.policies.lifecycle import PolicyStatus
from .intent import Actions, Entries, PermissionProposal, ShortText


class PolicyInput(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class PolicyConditions(PolicyInput):
    required_capability_ids: list[UUID] = Field(default_factory=list, max_length=32)
    not_before: AwareDatetime | None = None
    expires_at: AwareDatetime | None = None
    context_attributes: dict[ShortText, ShortText | StrictInt | StrictBool] = Field(default_factory=dict, max_length=24)

    @model_validator(mode="before")
    @classmethod
    def reject_ambiguous_context_keys(cls, value: object) -> object:
        if isinstance(value, dict) and isinstance(attributes := value.get("context_attributes"), dict):
            if any(isinstance(key, str) and key != key.strip() for key in attributes):
                raise ValueError("Context attribute keys must not have surrounding whitespace")
        return value

    @model_validator(mode="after")
    def normalize(self) -> Self:
        if self.not_before is not None:
            self.not_before = self.not_before.astimezone(timezone.utc)
        if self.expires_at is not None:
            self.expires_at = self.expires_at.astimezone(timezone.utc)
        if self.not_before is not None and self.expires_at is not None and self.not_before >= self.expires_at:
            raise ValueError("Policy expiration must follow its start")
        self.required_capability_ids = sorted(set(self.required_capability_ids))
        return self


class PolicyDefinition(PolicyInput):
    allowed_actions: Actions
    denied_actions: Actions
    approval_required_actions: Actions
    resource_scope: Entries
    sensitive_resources: Entries
    conditions: PolicyConditions = Field(default_factory=PolicyConditions)

    @model_validator(mode="after")
    def normalize(self) -> Self:
        actions = self.allowed_actions + self.denied_actions + self.approval_required_actions
        if len(actions) != len(set(actions)):
            raise ValueError("Action classifications must be disjoint and contain no duplicates")
        self.allowed_actions = sorted(self.allowed_actions)
        self.denied_actions = sorted(self.denied_actions)
        self.approval_required_actions = sorted(self.approval_required_actions)
        self.resource_scope = sorted(set(self.resource_scope))
        self.sensitive_resources = sorted(set(self.sensitive_resources))
        return self

    @classmethod
    def from_proposal(cls, permissions: PermissionProposal) -> Self:
        return cls(
            allowed_actions=permissions.allowed_actions,
            denied_actions=permissions.prohibited_actions,
            approval_required_actions=permissions.approval_required_actions,
            resource_scope=permissions.resource_scope,
            sensitive_resources=permissions.sensitive_resources,
        )


class CreatePolicy(PolicyInput):
    agent_id: UUID
    proposal_id: UUID


class CreatePolicyVersion(PolicyInput):
    base_version: Annotated[int, Field(strict=True, gt=0)]
    definition: PolicyDefinition


class ApprovePolicy(PolicyInput):
    approve: Literal[True]

    @model_validator(mode="before")
    @classmethod
    def require_boolean_confirmation(cls, value: object) -> object:
        if not isinstance(value, dict) or value.get("approve") is not True:
            raise ValueError("Explicit approval is required")
        return value


class PolicyVersionResponse(BaseModel):
    version: int
    status: PolicyStatus
    definition: PolicyDefinition
    created_at: datetime
    approved_at: datetime | None
    revoked_at: datetime | None
    superseded_at: datetime | None


class PolicyResponse(BaseModel):
    id: UUID
    owner_id: UUID
    source_proposal_id: UUID
    task_id: UUID
    agent_id: UUID
    created_at: datetime
    latest: PolicyVersionResponse
    active_version: int | None
