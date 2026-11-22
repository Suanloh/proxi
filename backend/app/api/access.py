from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..core.creds.tokens import InvalidCredential
from ..core.identity.lifecycle import InvalidAgentStatus
from ..schs.access import AccessCheck, CapabilityCreate, CapabilityResponse, CredentialIssued, SessionCreate, SessionResponse
from ..svcs.access import AccessRecordNotFound, AgentAccessService, CapabilityDenied, InvalidSession
from ..svcs.identity import AgentNotFound, OwnerNotAuthorized
from .owner_auth import bearer_required


def create_access_router(
    authenticate_owner: Callable[..., UUID],
    access_transaction: Callable[[Request], AbstractContextManager[AgentAccessService]],
) -> APIRouter:
    router = APIRouter(prefix="/agents/{agent_id}/sessions", tags=["agent access"])
    agent_bearer = HTTPBearer(auto_error=False, scheme_name="AgentBearer", bearerFormat="JWT")

    def access(request: Request) -> Iterator[AgentAccessService]:
        try:
            with access_transaction(request) as service:
                yield service
        except InvalidCredential:
            raise bearer_required() from None
        except (CapabilityDenied, OwnerNotAuthorized):
            raise HTTPException(status_code=403) from None
        except (AgentNotFound, AccessRecordNotFound):
            raise HTTPException(status_code=404) from None
        except (InvalidAgentStatus, InvalidSession):
            raise HTTPException(status_code=409) from None

    def authenticate_agent(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(agent_bearer)]) -> str:
        if credentials is None or len(credentials.credentials) > 2048:
            raise bearer_required()
        return credentials.credentials

    Owner = Annotated[UUID, Depends(authenticate_owner)]
    Token = Annotated[str, Depends(authenticate_agent)]
    Access = Annotated[AgentAccessService, Depends(access, scope="function")]

    @router.post("", status_code=201)
    def create_session(agent_id: UUID, body: SessionCreate, owner: Owner, service: Access) -> SessionResponse:
        return SessionResponse.from_session(service.create_session(owner, agent_id, body.ttl_seconds))

    @router.get("/{session_id}")
    def get_session(agent_id: UUID, session_id: UUID, owner: Owner, service: Access) -> SessionResponse:
        return SessionResponse.from_session(service.get_session(owner, agent_id, session_id))

    @router.post("/{session_id}/revoke")
    def revoke_session(agent_id: UUID, session_id: UUID, owner: Owner, service: Access) -> SessionResponse:
        return SessionResponse.from_session(service.revoke_session(owner, agent_id, session_id))

    @router.post("/{session_id}/credentials", status_code=201)
    def issue_credential(
        agent_id: UUID, session_id: UUID, owner: Owner, service: Access, response: Response,
    ) -> CredentialIssued:
        credential, token = service.issue_credential(owner, agent_id, session_id)
        response.headers["Cache-Control"] = "no-store"
        return CredentialIssued.model_validate({"id": credential.id, "token": token, "expires_at": credential.expires_at})

    @router.post("/{session_id}/credentials/{credential_id}/revoke", status_code=204)
    def revoke_credential(agent_id: UUID, session_id: UUID, credential_id: UUID, owner: Owner, service: Access) -> None:
        service.revoke_credential(owner, agent_id, session_id, credential_id)

    @router.post("/{session_id}/capabilities", status_code=201)
    def grant_capability(
        agent_id: UUID, session_id: UUID, body: CapabilityCreate, owner: Owner, service: Access,
    ) -> CapabilityResponse:
        return CapabilityResponse.model_validate(service.grant_capability(
            owner, agent_id, session_id, body.task_id, body.action, body.resource, body.ttl_seconds,
        ))

    @router.post("/{session_id}/capabilities/{capability_id}/revoke", status_code=204)
    def revoke_capability(agent_id: UUID, session_id: UUID, capability_id: UUID, owner: Owner, service: Access) -> None:
        service.revoke_capability(owner, agent_id, session_id, capability_id)

    @router.post("/{session_id}/access-check", status_code=204)
    def check_access(agent_id: UUID, session_id: UUID, body: AccessCheck, token: Token, service: Access) -> None:
        service.require_access(
            token, agent_id=agent_id, session_id=session_id, capability_id=body.capability_id,
            task_id=body.task_id, action=body.action, resource=body.resource,
        )

    return router
