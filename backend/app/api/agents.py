from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from secrets import compare_digest
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import SecretStr

from ..core.identity.lifecycle import InvalidAgentStatus
from ..core.repositories import AgentConflict
from ..models.records import Agent
from ..schs.agents import AgentCreate, AgentPatch, AgentResponse
from ..svcs.identity import AgentChanges, AgentIdentityService, AgentNotFound, OwnerNotAuthorized


def create_agents_router(
    owner_id: UUID | None,
    token: SecretStr | None,
    identity_transaction: Callable[[Request], AbstractContextManager[AgentIdentityService]],
) -> APIRouter:
    router = APIRouter(prefix="/agents", tags=["agents"])
    bearer = HTTPBearer(auto_error=False)
    expected_token = token.get_secret_value().encode("utf-8") if token is not None else None

    def manage_agents(
        request: Request,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> Iterator[tuple[AgentIdentityService, UUID]]:
        if owner_id is None or expected_token is None:
            raise HTTPException(status_code=503)
        if credentials is None or not compare_digest(credentials.credentials.encode("utf-8"), expected_token):
            raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Bearer"})
        try:
            with identity_transaction(request) as identity:
                identity.require_active_owner(owner_id)
                yield identity, owner_id
        except OwnerNotAuthorized:
            raise HTTPException(status_code=403) from None
        except AgentNotFound:
            raise HTTPException(status_code=404) from None
        except (AgentConflict, InvalidAgentStatus):
            raise HTTPException(status_code=409) from None

    Management = Annotated[tuple[AgentIdentityService, UUID], Depends(manage_agents, scope="function")]

    @router.post("", response_model=AgentResponse, status_code=201)
    def register_agent(body: AgentCreate, management: Management) -> Agent:
        identity, owner = management
        return identity.register(owner, body.name, body.type, body.description)

    @router.get("", response_model=list[AgentResponse])
    def list_agents(management: Management) -> list[Agent]:
        identity, owner = management
        return identity.list_owned(owner)

    @router.get("/{agent_id}", response_model=AgentResponse)
    def get_agent(agent_id: UUID, management: Management) -> Agent:
        identity, owner = management
        return identity.get_owned(owner, agent_id)

    @router.patch("/{agent_id}", response_model=AgentResponse)
    def update_agent(agent_id: UUID, body: AgentPatch, management: Management) -> Agent:
        identity, owner = management
        changes = cast(AgentChanges, body.model_dump(exclude_unset=True))
        return identity.update(owner, agent_id, **changes)

    @router.post("/{agent_id}/revoke", response_model=AgentResponse)
    def revoke_agent(agent_id: UUID, management: Management) -> Agent:
        identity, owner = management
        return identity.revoke(owner, agent_id)

    return router
