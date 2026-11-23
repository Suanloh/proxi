from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from pydantic import ValidationError

from ..core.creds.tokens import InvalidCredential
from ..core.identity.lifecycle import InvalidAgentStatus, require_active
from ..schs.authz import ActionRequest, ApprovalInfo, ContextAttributes, Decision, Outcome, Reason
from .access import AccessRecordNotFound, AgentAccessService, CapabilityDenied, session_status
from .identity import AgentIdentityService, AgentNotFound, OwnerNotAuthorized
from .policy_checks import (
    ApplicablePolicy, PolicyRetrieval, action_granted, attributes_allow, needs_approval, resource_allows, role_allows,
)


class TrustRestriction(Protocol):
    def allows(self, request: ActionRequest, attributes: ContextAttributes) -> bool: ...


class AuthorizationEngine:
    def __init__(
        self, identity: AgentIdentityService, access: AgentAccessService, policies: PolicyRetrieval,
        trust: TrustRestriction | None = None, clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._identity = identity
        self._access = access
        self._policies = policies
        self._trust = trust
        self._clock = clock

    def evaluate(
        self, request: ActionRequest, token: str, capability_id: UUID | None,
        *, trusted_context: ContextAttributes | None = None,
    ) -> Decision:
        def block(reason: Reason, policy: ApplicablePolicy | None = None) -> Decision:
            return Decision(request_id=request.request_id, outcome=Outcome.BLOCK, reason=reason,
                            failed_checks=(reason,), matched_policy=policy.match if policy else None)

        try:
            agent = self._identity.resolve(request.agent_id, for_update=True)
            self._identity.require_active_owner(agent.owner_id)
            require_active(agent.status)
        except (AgentNotFound, OwnerNotAuthorized):
            return block(Reason.IDENTITY_INVALID)
        except InvalidAgentStatus:
            return block(Reason.AGENT_INACTIVE)

        try:
            session = self._access.get_bound_session(agent.id, request.session_id)
        except AccessRecordNotFound:
            return block(Reason.SESSION_INVALID)
        now = self._clock()
        status = session_status(session, now)
        if status != "active":
            return block(Reason.SESSION_REVOKED if status == "revoked" else Reason.SESSION_EXPIRED)

        try:
            claims = self._access.decode_bound_credential(token, agent.id, session.id)
            self._access.require_current_credential(claims, now)
        except InvalidCredential:
            return block(Reason.CREDENTIAL_INVALID)
        if capability_id is None:
            return block(Reason.CAPABILITY_DENIED)
        try:
            self._access.require_capability(agent.id, session.id, capability_id, request.task_id,
                                            request.action, request.resource, now)
        except CapabilityDenied:
            return block(Reason.CAPABILITY_DENIED)

        try:
            active = self._policies.active(agent, request.task_id, now)
        except ValidationError:
            return block(Reason.POLICY_INVALID)
        for policy in active:
            if request.action in policy.definition.denied_actions:
                return block(Reason.EXPLICIT_DENIAL, policy)
        scoped = [policy for policy in active if resource_allows(policy, request.resource)]
        if active and not scoped:
            return block(Reason.RESOURCE_OUT_OF_SCOPE, active[0])
        if not active:
            return block(Reason.NO_ACTIVE_POLICY)
        if not role_allows(agent, request):
            return block(Reason.ROLE_DENIED)
        candidates = [policy for policy in scoped if action_granted(policy, request.action)]
        if not candidates:
            return block(Reason.ACTION_NOT_GRANTED, scoped[0])
        context = dict(trusted_context or {})
        grants = [policy for policy in candidates if attributes_allow(policy, capability_id, context)]
        if not grants:
            return block(Reason.CONDITIONS_NOT_MET, candidates[0])
        if self._trust is not None and self._trust.allows(request.model_copy(deep=True), context.copy()) is not True:
            return block(Reason.TRUST_RESTRICTED, grants[0])
        for policy in scoped:
            if needs_approval(policy, request) and attributes_allow(policy, capability_id, context):
                return Decision(
                    request_id=request.request_id, outcome=Outcome.HOLD, reason=Reason.APPROVAL_REQUIRED,
                    matched_policy=policy.match,
                    required_approval=ApprovalInfo(reviewer_id=agent.owner_id, action=request.action,
                                                   resource=request.resource),
                )
        return Decision(request_id=request.request_id, outcome=Outcome.ALLOW, reason=Reason.CHECKS_PASSED,
                        matched_policy=grants[0].match)
