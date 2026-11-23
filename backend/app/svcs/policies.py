import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from ..core.policies.lifecycle import PolicyConflict, PolicyStatus, is_approved_active
from ..core.repositories import PolicyRepository
from ..models.records import Policy, PolicyVersion
from ..schs.policies import PolicyDefinition, PolicyResponse, PolicyVersionResponse
from .identity import AgentIdentityService
from .intent import IntentReview


class PolicyNotFound(LookupError):
    pass


class PolicyManagement:
    def __init__(self, identity: AgentIdentityService, intents: IntentReview, policies: PolicyRepository) -> None:
        self._identity = identity
        self._intents = intents
        self._policies = policies

    def create(self, owner_id: UUID, agent_id: UUID, proposal_id: UUID) -> PolicyResponse:
        self._intents.require_active_agent(owner_id, agent_id, for_update=True)
        proposal = self._intents.get_proposal(owner_id, agent_id, proposal_id)
        if proposal is None:
            raise PolicyNotFound("Proposal not found")
        definition = PolicyDefinition.from_proposal(proposal.proposed_permissions)
        policy_id = uuid4()
        policy = self._policies.add_policy(Policy(
            id=policy_id, owner_id=owner_id, name=str(policy_id), agent_id=agent_id,
            task_id=proposal.task_id, source_proposal_id=proposal.id,
        ))
        draft = self._add_draft(policy_id, 1, definition)
        return self._response(policy, draft, None)

    def list_owned(self, owner_id: UUID) -> list[PolicyResponse]:
        self._identity.require_active_owner(owner_id)
        return [self._details(policy) for policy in self._policies.list_owned(owner_id)]

    def details(self, owner_id: UUID, policy_id: UUID) -> PolicyResponse:
        return self._details(self._get_owned(owner_id, policy_id))

    def history(self, owner_id: UUID, policy_id: UUID) -> list[PolicyVersionResponse]:
        self._get_owned(owner_id, policy_id)
        return [self._version_response(version) for version in self._policies.versions(policy_id)]

    def revise(
        self, owner_id: UUID, policy_id: UUID, base_version: int, definition: PolicyDefinition,
    ) -> PolicyVersionResponse:
        self._get_owned(owner_id, policy_id, for_update=True)
        versions = self._policies.versions(policy_id)
        latest = versions[-1]
        if latest.version != base_version:
            raise PolicyConflict("Policy version has changed")
        if latest.status in {PolicyStatus.DRAFT, PolicyStatus.PENDING_APPROVAL}:
            raise PolicyConflict("Resolve the outstanding policy draft first")
        serialized = json.dumps(definition.model_dump(mode="json"), sort_keys=True)
        active = self._active(versions)
        if any(serialized == json.dumps(version.definition, sort_keys=True)
               for version in (latest, active) if version is not None):
            raise PolicyConflict("Policy definition has not changed")
        return self._version_response(self._add_draft(policy_id, latest.version + 1, definition))

    def submit(self, owner_id: UUID, policy_id: UUID, number: int) -> PolicyVersionResponse:
        self._get_owned(owner_id, policy_id, for_update=True)
        version = self._find_version(self._policies.versions(policy_id), number)
        return self._change_status(version, PolicyStatus.PENDING_APPROVAL)

    def approve(self, owner_id: UUID, policy_id: UUID, number: int) -> PolicyVersionResponse:
        policy = self._get_owned(owner_id, policy_id, for_update=True)
        versions = self._policies.versions(policy_id)
        target = self._find_version(versions, number)
        if target.status != PolicyStatus.PENDING_APPROVAL:
            raise PolicyConflict("Only a pending policy version can be approved")
        if policy.agent_id is None:
            raise PolicyConflict("Missing agent binding")
        self._intents.require_active_agent(owner_id, policy.agent_id, for_update=True)
        definition = self._version_response(target).definition
        now = datetime.now(timezone.utc)
        if definition.conditions.expires_at is not None and definition.conditions.expires_at <= now:
            raise PolicyConflict("Expired policy versions cannot be approved")
        active = self._active(versions)
        if active is not None:
            self._policies.transition(active.id, PolicyStatus.SUPERSEDED, now)
        return self._version_response(self._policies.transition(target.id, PolicyStatus.ACTIVE, now))

    def revoke(self, owner_id: UUID, policy_id: UUID, number: int) -> PolicyVersionResponse:
        self._get_owned(owner_id, policy_id, for_update=True)
        version = self._find_version(self._policies.versions(policy_id), number)
        return self._change_status(version, PolicyStatus.REVOKED)

    def _get_owned(self, owner_id: UUID, policy_id: UUID, *, for_update: bool = False) -> Policy:
        self._identity.require_active_owner(owner_id)
        policy = self._policies.get_owned(owner_id, policy_id, for_update=for_update)
        if policy is None:
            raise PolicyNotFound("Policy not found")
        return policy

    def _details(self, policy: Policy) -> PolicyResponse:
        versions = self._policies.versions(policy.id)
        return self._response(policy, versions[-1], self._active(versions))

    def _add_draft(self, policy_id: UUID, number: int, definition: PolicyDefinition) -> PolicyVersion:
        return self._policies.add_version(PolicyVersion(
            policy_id=policy_id, version=number, definition=definition.model_dump(mode="json"),
        ))

    def _change_status(self, version: PolicyVersion, target: PolicyStatus) -> PolicyVersionResponse:
        return self._version_response(self._policies.transition(version.id, target, datetime.now(timezone.utc)))

    @staticmethod
    def _find_version(versions: list[PolicyVersion], number: int) -> PolicyVersion:
        for version in versions:
            if version.version == number:
                return version
        raise PolicyNotFound("Policy version not found")

    @staticmethod
    def _active(versions: list[PolicyVersion]) -> PolicyVersion | None:
        return next((version for version in versions if is_approved_active(version)), None)

    @staticmethod
    def _version_response(version: PolicyVersion) -> PolicyVersionResponse:
        if version.definition is None or version.created_at is None:
            raise RuntimeError("Missing persisted policy snapshot")
        return PolicyVersionResponse(
            version=version.version, status=PolicyStatus(version.status),
            definition=PolicyDefinition.model_validate(version.definition), created_at=version.created_at,
            approved_at=version.approved_at, revoked_at=version.revoked_at, superseded_at=version.superseded_at,
        )

    @classmethod
    def _response(cls, policy: Policy, latest: PolicyVersion, active: PolicyVersion | None) -> PolicyResponse:
        if (policy.source_proposal_id is None or policy.task_id is None or policy.agent_id is None
                or policy.created_at is None):
            raise RuntimeError("Missing persisted policy scope")
        return PolicyResponse(
            id=policy.id, owner_id=policy.owner_id, source_proposal_id=policy.source_proposal_id,
            task_id=policy.task_id, agent_id=policy.agent_id, created_at=policy.created_at,
            latest=cls._version_response(latest), active_version=active.version if active is not None else None,
        )
