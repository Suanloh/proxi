from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from ..core.identity.lifecycle import InvalidAgentStatus
from ..svcs.identity import AgentIdentityService, AgentNotFound, OwnerNotAuthorized
from ..svcs.trust import DynamicTrust, TrustReviewConflict


def create_trust_router(
    authenticate_owner: Callable[..., UUID],
    transaction: Callable[[Request], AbstractContextManager[tuple[DynamicTrust, AgentIdentityService]]],
) -> APIRouter:
    router = APIRouter(prefix="/agents", tags=["trust"])
    Owner = Annotated[UUID, Depends(authenticate_owner)]

    @router.post("/{agent_id}/trust/review", status_code=204)
    def review(agent_id: UUID, request: Request, owner: Owner) -> Response:
        try:
            with transaction(request) as (trust, identity):
                trust.review(identity, owner, agent_id)
        except OwnerNotAuthorized:
            raise HTTPException(status_code=403) from None
        except AgentNotFound:
            raise HTTPException(status_code=404) from None
        except (InvalidAgentStatus, TrustReviewConflict):
            raise HTTPException(status_code=409) from None
        return Response(status_code=204, headers={"Cache-Control": "no-store"})

    return router
