from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.policies.lifecycle import PolicyConflict, PolicyStatus, is_approved_active, transition
from app.models.records import PolicyVersion
from app.schs.intent import PermissionProposal
from app.schs.policies import PolicyConditions, PolicyDefinition


def test_proposal_conversion_is_independent_of_input_order() -> None:
    common = {"prohibited_actions": ["file.write"], "approval_required_actions": ["browser.submit"],
              "sensitive_resources": ["private documents"]}
    first = PermissionProposal(**common, allowed_actions=["browser.read", "browser.navigate"],
                               resource_scope=["public reports", "public records"])
    second = PermissionProposal(**common, allowed_actions=["browser.navigate", "browser.read"],
                                resource_scope=["public records", "public reports"])
    assert PolicyDefinition.from_proposal(first).model_dump_json() == PolicyDefinition.from_proposal(second).model_dump_json()
    with pytest.raises(ValidationError, match="surrounding whitespace"):
        PolicyConditions.model_validate({"context_attributes": {"network": "local", " network": "remote"}})


def test_discarded_draft_cannot_enter_approved_lifecycle() -> None:
    at = datetime.now(timezone.utc)
    draft = PolicyVersion(policy_id=uuid4(), version=1, definition={})
    assert not is_approved_active(draft)
    discarded = transition(draft, PolicyStatus.REVOKED, at)
    assert discarded.revoked_at == at and discarded.approved_at is None
    assert not is_approved_active(discarded)
    with pytest.raises(PolicyConflict):
        transition(discarded, PolicyStatus.PENDING_APPROVAL, at)
