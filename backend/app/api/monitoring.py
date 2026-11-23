from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from ..schs.monitoring import AuditEntry, EventFilters, SecurityEntry
from ..svcs.identity import OwnerNotAuthorized
from ..svcs.monitoring import EventQuery


def create_monitoring_router(
    authenticate_owner: Callable[..., UUID],
    transaction: Callable[[Request, UUID], AbstractContextManager[EventQuery]],
) -> APIRouter:
    router = APIRouter(tags=["monitoring"])
    Owner = Annotated[UUID, Depends(authenticate_owner)]
    Filters = Annotated[EventFilters, Query()]

    @router.get("/audit-logs")
    def audit(request: Request, response: Response, owner: Owner, filters: Filters) -> list[AuditEntry]:
        response.headers["Cache-Control"] = "no-store"
        try:
            with transaction(request, owner) as query:
                return query.audit(owner, filters)
        except OwnerNotAuthorized:
            raise HTTPException(status_code=403) from None

    @router.get("/security-events")
    def security(request: Request, response: Response, owner: Owner, filters: Filters) -> list[SecurityEntry]:
        response.headers["Cache-Control"] = "no-store"
        try:
            with transaction(request, owner) as query:
                return query.security(owner, filters)
        except OwnerNotAuthorized:
            raise HTTPException(status_code=403) from None

    return router
