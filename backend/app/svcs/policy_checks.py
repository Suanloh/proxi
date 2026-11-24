from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ..core.policies.lifecycle import is_approved_active
from ..core.repositories import PolicyRepository
from ..models.records import Agent
from ..schs.authz import ActionRequest, ContextAttributes, PolicyMatch
from ..schs.policies import PolicyDefinition


@dataclass(frozen=True)
class ApplicablePolicy:
    match: PolicyMatch
    definition: PolicyDefinition
    source_proposal_id: UUID


class PolicyRetrieval:
    def __init__(self, policies: PolicyRepository) -> None:
        self._policies = policies

    def active(self, agent: Agent, task_id: UUID | None, now: datetime) -> list[ApplicablePolicy]:
        result = []
        for policy in sorted(self._policies.list_owned(agent.owner_id), key=lambda item: item.id):
            if (policy.owner_id != agent.owner_id or policy.agent_id != agent.id or policy.task_id != task_id
                    or task_id is None or policy.source_proposal_id is None or policy.status != "active"):
                continue
            for version in self._policies.versions(policy.id):
                if (not is_approved_active(version) or version.policy_id != policy.id or version.approved_at is None
                        or version.approved_at > now or version.revoked_at is not None
                        or version.superseded_at is not None):
                    continue
                definition = PolicyDefinition.model_validate(version.definition)
                conditions = definition.conditions
                if ((conditions.not_before is not None and now < conditions.not_before)
                        or (conditions.expires_at is not None and now >= conditions.expires_at)):
                    continue
                result.append(ApplicablePolicy(
                    PolicyMatch(policy_id=policy.id, version=version.version, version_id=version.id),
                    definition, policy.source_proposal_id,
                ))
        return result


def role_allows(agent: Agent, request: ActionRequest) -> bool:
    return agent.type == request.integration_type


def resource_allows(policy: ApplicablePolicy, resource: str) -> bool:
    return resource in policy.definition.resource_scope


def context_allows(policy: ApplicablePolicy, attributes: ContextAttributes) -> bool:
    return all(key in attributes and type(attributes[key]) is type(expected) and attributes[key] == expected
               for key, expected in policy.definition.conditions.context_attributes.items())


def attributes_allow(policy: ApplicablePolicy, capability_id: UUID, attributes: ContextAttributes) -> bool:
    required = policy.definition.conditions.required_capability_ids
    return all(required_id == capability_id for required_id in required) and context_allows(policy, attributes)


def action_granted(policy: ApplicablePolicy, action: str) -> bool:
    return action in policy.definition.allowed_actions or action in policy.definition.approval_required_actions


def needs_approval(policy: ApplicablePolicy, request: ActionRequest) -> bool:
    return (request.action in policy.definition.approval_required_actions
            or request.resource in policy.definition.sensitive_resources)
