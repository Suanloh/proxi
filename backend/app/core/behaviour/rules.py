from dataclasses import dataclass
from enum import StrEnum

from ...schs.authz import Reason


class Rule(StrEnum):
    NORMAL = "normal_authorized_operation"
    UNUSUAL = "unusual_action"
    DENIED = "denied_action"
    REPEATED_DENIED = "repeated_denied_action"
    RESTRICTED_RESOURCE = "restricted_resource_attempt"
    BOUNDARY = "permission_boundary_violation"
    SEQUENCE = "unexpected_action_sequence"
    APPROVAL = "approval_requested"
    REPEATED_APPROVAL = "repeated_approval_requests"
    SESSION = "session_anomaly"
    TRUST_BLOCK = "trust_restricted"
    EXECUTED = "execution_succeeded"
    EXECUTION_FAILED = "execution_failed"
    RECOVERY = "sustained_compliant_behaviour"
    REVIEW = "owner_review"


@dataclass(frozen=True)
class Finding:
    rule: Rule
    reason: str


_DENIALS = {
    Reason.EXPLICIT_DENIAL: Rule.DENIED,
    Reason.RESOURCE_OUT_OF_SCOPE: Rule.RESTRICTED_RESOURCE,
    Reason.CAPABILITY_DENIED: Rule.BOUNDARY,
    Reason.ROLE_DENIED: Rule.BOUNDARY,
    Reason.NO_ACTIVE_POLICY: Rule.UNUSUAL,
    Reason.ACTION_NOT_GRANTED: Rule.UNUSUAL,
    Reason.CONDITIONS_NOT_MET: Rule.BOUNDARY,
}
DENIAL_REASONS = frozenset(_DENIALS)


def denial(reason: Reason) -> Finding | None:
    if reason in _DENIALS:
        return Finding(_DENIALS[reason], reason)
    if reason == Reason.TRUST_RESTRICTED:
        return Finding(Rule.TRUST_BLOCK, reason)
    return None
