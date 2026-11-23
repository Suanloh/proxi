from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request

from ..core.identity.lifecycle import InvalidAgentStatus
from ..core.policies.lifecycle import PolicyConflict
from ..schs.policies import ApprovePolicy, CreatePolicy, CreatePolicyVersion, PolicyResponse, PolicyVersionResponse
from ..svcs.identity import AgentNotFound, OwnerNotAuthorized
from ..svcs.policies import PolicyManagement, PolicyNotFound

VersionNumber = Annotated[int, Path(gt=0, le=2_147_483_647)]


def create_policy_router(
    authenticate_owner: Callable[..., UUID],
    transaction: Callable[[Request], AbstractContextManager[PolicyManagement]],
) -> APIRouter:
    router = APIRouter(prefix="/policies", tags=["policies"])
    Owner = Annotated[UUID, Depends(authenticate_owner)]

    @contextmanager
    def policy_transaction(request: Request) -> Iterator[PolicyManagement]:
        try:
            with transaction(request) as management:
                yield management
        except OwnerNotAuthorized:
            raise HTTPException(status_code=403) from None
        except (AgentNotFound, PolicyNotFound):
            raise HTTPException(status_code=404) from None
        except (InvalidAgentStatus, PolicyConflict):
            raise HTTPException(status_code=409) from None

    @router.post("", status_code=201)
    def create(request: Request, body: CreatePolicy, owner: Owner) -> PolicyResponse:
        with policy_transaction(request) as management:
            return management.create(owner, body.agent_id, body.proposal_id)

    @router.get("")
    def list_owned(request: Request, owner: Owner) -> list[PolicyResponse]:
        with policy_transaction(request) as management:
            return management.list_owned(owner)

    @router.get("/{policy_id}")
    def details(request: Request, policy_id: UUID, owner: Owner) -> PolicyResponse:
        with policy_transaction(request) as management:
            return management.details(owner, policy_id)

    @router.get("/{policy_id}/versions")
    def history(request: Request, policy_id: UUID, owner: Owner) -> list[PolicyVersionResponse]:
        with policy_transaction(request) as management:
            return management.history(owner, policy_id)

    @router.post("/{policy_id}/versions", status_code=201)
    def revise(request: Request, policy_id: UUID, body: CreatePolicyVersion, owner: Owner) -> PolicyVersionResponse:
        with policy_transaction(request) as management:
            return management.revise(owner, policy_id, body.base_version, body.definition)

    @router.post("/{policy_id}/versions/{version}/submit")
    def submit(request: Request, policy_id: UUID, version: VersionNumber, owner: Owner) -> PolicyVersionResponse:
        with policy_transaction(request) as management:
            return management.submit(owner, policy_id, version)

    @router.post("/{policy_id}/versions/{version}/approve")
    def approve(
        request: Request, policy_id: UUID, version: VersionNumber, body: ApprovePolicy, owner: Owner,
    ) -> PolicyVersionResponse:
        with policy_transaction(request) as management:
            return management.approve(owner, policy_id, version)

    @router.post("/{policy_id}/versions/{version}/revoke")
    def revoke(request: Request, policy_id: UUID, version: VersionNumber, owner: Owner) -> PolicyVersionResponse:
        with policy_transaction(request) as management:
            return management.revoke(owner, policy_id, version)

    return router
