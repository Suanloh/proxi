from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from ..schs.dashboard import DashboardAgent, DashboardIntegration, DashboardOverview, TrustSummary
from ..svcs.dashboard import DashboardQuery
from ..svcs.identity import AgentIdentityService, AgentNotFound, OwnerNotAuthorized


def create_dashboard_router(
    authenticate_owner: Callable[..., UUID],
    transaction: Callable[[Request], AbstractContextManager[tuple[DashboardQuery, AgentIdentityService]]],
    integrations: Callable[[], list[DashboardIntegration]],
) -> APIRouter:
    router = APIRouter(prefix="/dashboard", tags=["dashboard"])
    Owner = Annotated[UUID, Depends(authenticate_owner)]

    @router.get("/overview")
    def overview(request: Request, response: Response, owner: Owner) -> DashboardOverview:
        response.headers["Cache-Control"] = "no-store"
        with transaction(request) as (query, identity):
            require_owner(identity, owner)
            return query.overview(owner)

    @router.get("/agents/{agent_id}")
    def agent(agent_id: UUID, request: Request, response: Response, owner: Owner) -> DashboardAgent:
        response.headers["Cache-Control"] = "no-store"
        with transaction(request) as (query, identity):
            require_owner(identity, owner)
            try:
                identity.get_owned(owner, agent_id)
            except AgentNotFound:
                raise HTTPException(status_code=404) from None
            return query.agent(agent_id)

    @router.get("/trust")
    def trust(request: Request, response: Response, owner: Owner) -> list[TrustSummary]:
        response.headers["Cache-Control"] = "no-store"
        with transaction(request) as (query, identity):
            require_owner(identity, owner)
            return query.trust(owner)

    @router.get("/integrations")
    def status(request: Request, response: Response, owner: Owner) -> list[DashboardIntegration]:
        response.headers["Cache-Control"] = "no-store"
        with transaction(request) as (_, identity):
            require_owner(identity, owner)
            return integrations()

    return router


def require_owner(identity: AgentIdentityService, owner: UUID) -> None:
    try:
        identity.require_active_owner(owner)
    except OwnerNotAuthorized:
        raise HTTPException(status_code=403) from None
