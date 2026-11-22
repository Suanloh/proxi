from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StrictBool, StringConstraints, model_validator


def _valid_text(value: str) -> str:
    if "\x00" in value:
        raise ValueError("Text must not contain NUL")
    value.encode("utf-8")
    return value


ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256),
                      AfterValidator(_valid_text)]
TaskText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000),
                     AfterValidator(_valid_text)]
Action = Annotated[str, StringConstraints(max_length=96, pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")]
Actions = Annotated[list[Action], Field(max_length=32)]
Entries = Annotated[list[ShortText], Field(max_length=24)]


class IntentRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", hide_input_in_errors=True)

    task: TaskText
    share_with_deepseek: StrictBool

    @model_validator(mode="after")
    def require_sharing_consent(self) -> Self:
        if not self.share_with_deepseek:
            raise ValueError("Explicit consent to send non-sensitive task text is required")
        return self


class PermissionProposal(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", hide_input_in_errors=True)

    allowed_actions: Actions
    prohibited_actions: Actions
    approval_required_actions: Actions
    resource_scope: Entries
    sensitive_resources: Entries

    @model_validator(mode="after")
    def require_disjoint_actions(self) -> Self:
        actions = self.allowed_actions + self.prohibited_actions + self.approval_required_actions
        if len(actions) != len(set(actions)):
            raise ValueError("Action lists must not contain duplicates or conflicting classifications")
        return self


class IntentInterpretation(PermissionProposal):
    task_objective: ShortText
    task_description: TaskText
    risk_indicators: Entries
    interpretation_explanation: TaskText

    def permissions(self) -> PermissionProposal:
        return PermissionProposal(
            allowed_actions=self.allowed_actions,
            prohibited_actions=self.prohibited_actions,
            approval_required_actions=self.approval_required_actions,
            resource_scope=self.resource_scope,
            sensitive_resources=self.sensitive_resources,
        )


class IntentProposal(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", hide_input_in_errors=True)

    interpretation: IntentInterpretation
    proposed_permissions: PermissionProposal


class IntentProposalResponse(IntentProposal):
    id: UUID
    task_id: UUID
    status: Literal["proposed"] = "proposed"
    created_at: datetime
