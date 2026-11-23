from collections.abc import Mapping
from enum import StrEnum
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue

from ..models.records import AgentType
from .intent import Action, ShortText

ContextAttributes = Mapping[str, str | int | bool]


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True, allow_inf_nan=False)

    request_id: UUID
    agent_id: UUID
    session_id: UUID
    action: Action
    resource: ShortText
    params: dict[str, JsonValue] = Field(default_factory=dict, max_length=64, repr=False)
    timestamp: AwareDatetime
    integration_type: AgentType
    task_id: UUID | None = None


class AuthorizationCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: ActionRequest
    capability_id: UUID | None = None


class Outcome(StrEnum):
    ALLOW = "ALLOW"
    HOLD = "HOLD"
    BLOCK = "BLOCK"


class Reason(StrEnum):
    IDENTITY_INVALID = "identity_invalid"
    AGENT_INACTIVE = "agent_inactive"
    SESSION_INVALID = "session_invalid"
    SESSION_EXPIRED = "session_expired"
    SESSION_REVOKED = "session_revoked"
    CREDENTIAL_INVALID = "credential_invalid"
    CAPABILITY_DENIED = "capability_denied"
    POLICY_INVALID = "policy_invalid"
    EXPLICIT_DENIAL = "explicit_denial"
    RESOURCE_OUT_OF_SCOPE = "resource_out_of_scope"
    NO_ACTIVE_POLICY = "no_active_policy"
    ROLE_DENIED = "role_denied"
    ACTION_NOT_GRANTED = "action_not_granted"
    CONDITIONS_NOT_MET = "conditions_not_met"
    TRUST_RESTRICTED = "trust_restricted"
    APPROVAL_REQUIRED = "approval_required"
    CHECKS_PASSED = "checks_passed"
    ADAPTER_UNAVAILABLE = "adapter_unavailable"


class PolicyMatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy_id: UUID
    version: int
    version_id: UUID


class ApprovalInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    reviewer_id: UUID
    action: Action
    resource: ShortText


class Decision(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: UUID
    outcome: Outcome
    reason: Reason
    matched_policy: PolicyMatch | None = None
    failed_checks: tuple[Reason, ...] = ()
    required_approval: ApprovalInfo | None = None
