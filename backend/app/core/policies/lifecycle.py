from dataclasses import replace
from datetime import datetime
from enum import StrEnum

from ...models.records import PolicyVersion


class PolicyStatus(StrEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    REVOKED = "revoked"
    SUPERSEDED = "superseded"


class PolicyConflict(ValueError):
    pass


_TRANSITIONS = {
    PolicyStatus.DRAFT: {PolicyStatus.PENDING_APPROVAL, PolicyStatus.REVOKED},
    PolicyStatus.PENDING_APPROVAL: {PolicyStatus.ACTIVE, PolicyStatus.REVOKED},
    PolicyStatus.ACTIVE: {PolicyStatus.REVOKED, PolicyStatus.SUPERSEDED},
    PolicyStatus.REVOKED: set(),
    PolicyStatus.SUPERSEDED: set(),
}


def transition(version: PolicyVersion, target: PolicyStatus, at: datetime) -> PolicyVersion:
    if version.definition is None or target not in _TRANSITIONS[PolicyStatus(version.status)]:
        raise PolicyConflict("Invalid policy transition")
    return replace(
        version,
        status=target,
        approved_at=at if target is PolicyStatus.ACTIVE else version.approved_at,
        revoked_at=at if target is PolicyStatus.REVOKED else version.revoked_at,
        superseded_at=at if target is PolicyStatus.SUPERSEDED else version.superseded_at,
    )


def is_approved_active(version: PolicyVersion) -> bool:
    return (
        version.status == PolicyStatus.ACTIVE and version.definition is not None and version.approved_at is not None
    )
