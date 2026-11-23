from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from ..schs.approvals import ApprovalDetails, ApprovalStatus
from ..svcs.approvals import ActionApprovals, ApprovalConflict, ApprovalNotFound
from ..svcs.identity import AgentNotFound, OwnerNotAuthorized


def create_approval_router(
    authenticate_owner: Callable[..., UUID],
    transaction: Callable[[Request], AbstractContextManager[ActionApprovals]],
) -> APIRouter:
    router = APIRouter(prefix="/approvals", tags=["approvals"])
    Owner = Annotated[UUID, Depends(authenticate_owner)]

    @contextmanager
    def service(request: Request, response: Response) -> Iterator[ActionApprovals]:
        response.headers["Cache-Control"] = "no-store"
        try:
            with transaction(request) as approvals:
                yield approvals
        except OwnerNotAuthorized:
            raise HTTPException(status_code=403) from None
        except (ApprovalNotFound, AgentNotFound):
            raise HTTPException(status_code=404) from None
        except ApprovalConflict:
            raise HTTPException(status_code=409) from None

    @router.get("")
    def list_approvals(request: Request, response: Response, owner: Owner,
                       history: bool = False, limit: Annotated[int, Query(ge=1, le=100)] = 50,
                       offset: Annotated[int, Query(ge=0, le=2_147_483_647)] = 0) -> list[ApprovalDetails]:
        with service(request, response) as approvals:
            return approvals.list_owned(owner, pending=not history, limit=limit, offset=offset)

    @router.get("/{approval_id}")
    def get_approval(request: Request, response: Response, approval_id: UUID, owner: Owner) -> ApprovalDetails:
        with service(request, response) as approvals:
            return approvals.get(owner, approval_id)

    @router.post("/{approval_id}/approve")
    def approve(request: Request, response: Response, approval_id: UUID, owner: Owner) -> ApprovalDetails:
        with service(request, response) as approvals:
            return approvals.review(owner, approval_id, ApprovalStatus.APPROVED)

    @router.post("/{approval_id}/reject")
    def reject(request: Request, response: Response, approval_id: UUID, owner: Owner) -> ApprovalDetails:
        with service(request, response) as approvals:
            return approvals.review(owner, approval_id, ApprovalStatus.REJECTED)

    @router.post("/{approval_id}/cancel")
    def cancel(request: Request, response: Response, approval_id: UUID, owner: Owner) -> ApprovalDetails:
        with service(request, response) as approvals:
            return approvals.review(owner, approval_id, ApprovalStatus.CANCELLED)

    return router
