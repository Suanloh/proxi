from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from pydantic import ValidationError

from ..core.creds.tokens import InvalidCredential
from ..core.identity.lifecycle import InvalidAgentStatus, require_active
from ..schs.authz import ActionRequest, ApprovalInfo, ContextAttributes, Decision, Outcome, Reason
from .access import AccessRecordNotFound, AgentAccessService, CapabilityDenied, session_status
from .approvals import ActionApprovals, ApprovalClaim
from .identity import AgentIdentityService, AgentNotFound, OwnerNotAuthorized
from .trust import DynamicTrust
from .policy_checks import (
    ApplicablePolicy, PolicyRetrieval, action_granted, attributes_allow, needs_approval, resource_allows, role_allows,
)


class TrustRestriction(Protocol):
    def allows(self, request: ActionRequest, attributes: ContextAttributes) -> bool: ...


class AuthorizationEngine:
    def __init__(
        self, identity: AgentIdentityService, access: AgentAccessService, policies: PolicyRetrieval,
        trust: TrustRestriction | None = None, clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        *, approvals: ActionApprovals | None = None, behaviour: DynamicTrust | None = None,
    ) -> None:
        self.approvals = approvals
        self.behaviour = behaviour
        self._identity = identity
        self._access = access
        self._policies = policies
        self._trust = trust
        self._clock = clock

    def evaluate(
        self, request: ActionRequest, token: str, capability_id: UUID | None,
        *, trusted_context: ContextAttributes | None = None, _claim: ApprovalClaim | None = None,
        _dispatch: bool = False,
    ) -> Decision:
        attributable = False

        def block(reason: Reason, policy: ApplicablePolicy | None = None) -> Decision:
            if attributable and self.behaviour is not None:
                self.behaviour.blocked(request, reason)
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
        session_reason = None if status == "active" else (
            Reason.SESSION_REVOKED if status == "revoked" else Reason.SESSION_EXPIRED
        )
        if session_reason is not None and self.behaviour is None:
            return block(session_reason)
        try:
            claims = self._access.decode_bound_credential(token, agent.id, session.id)
            self._access.require_current_credential(claims, now)
        except InvalidCredential:
            return block(session_reason or Reason.CREDENTIAL_INVALID)
        if session_reason is not None:
            if self.behaviour is not None:
                self.behaviour.session_anomaly(request, session_reason)
            return block(session_reason)
        attributable = True
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
        gates = [policy for policy in scoped
                 if needs_approval(policy, request) and attributes_allow(policy, capability_id, context)]
        versions = tuple(policy.match.version_id for policy in gates)
        if _claim is not None:
            if (not gates or versions != _claim.policy_version_ids or agent.owner_id != _claim.reviewer_id
                    or self._clock() >= _claim.expires_at):
                return block(Reason.APPROVAL_INVALID)
        elif gates:
            return Decision(
                request_id=request.request_id, outcome=Outcome.HOLD, reason=Reason.APPROVAL_REQUIRED,
                matched_policy=gates[0].match,
                required_approval=ApprovalInfo(reviewer_id=agent.owner_id, action=request.action,
                                               resource=request.resource, policy_version_ids=versions),
            )
        if _dispatch and self.behaviour is not None:
            self.behaviour.inspect_grant(request, (policy.source_proposal_id for policy in grants))
            if not self.behaviour.allows(request, context):
                return block(Reason.TRUST_RESTRICTED, grants[0])
        return Decision(request_id=request.request_id, outcome=Outcome.ALLOW, reason=Reason.CHECKS_PASSED,
                        matched_policy=grants[0].match)
