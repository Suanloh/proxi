from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..core.creds.tokens import CredentialClaims, CredentialCodec, ExpiredCredential, InvalidCredential
from ..schs.authz import ActionRequest, AuthorizationCheck, Decision
from ..svcs.authz import AuthorizationEngine
from .owner_auth import bearer_required


def bound_agent_token(
    credentials: HTTPAuthorizationCredentials | None, codec: CredentialCodec | None,
    action: ActionRequest, record_denial: Callable[[CredentialClaims | None], None],
) -> str:
    if credentials is None or len(credentials.credentials) > 2048:
        record_denial(None)
        raise bearer_required()
    if codec is None:
        raise HTTPException(status_code=503)
    token = credentials.credentials
    expected = (action.agent_id, action.session_id)
    try:
        claims = codec.decode(token)
    except ExpiredCredential as exc:
        record_denial(exc.claims if (exc.claims.agent_id, exc.claims.session_id) == expected else None)
        raise bearer_required() from None
    except InvalidCredential:
        record_denial(None)
        raise bearer_required() from None
    if (claims.agent_id, claims.session_id) != expected:
        record_denial(None)
        raise bearer_required()
    return token


def create_authorization_router(
    codec: CredentialCodec | None,
    transaction: Callable[[Request], AbstractContextManager[AuthorizationEngine]],
    record_denial: Callable[[Request, CredentialClaims | None], None] = lambda _request, _claims: None,
) -> APIRouter:
    router = APIRouter(prefix="/authorization", tags=["authorization"])
    bearer = HTTPBearer(auto_error=False, scheme_name="AgentBearer", bearerFormat="JWT")

    @router.post("/check")
    def check(
        body: AuthorizationCheck, request: Request, response: Response,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> Decision:
        token = bound_agent_token(credentials, codec, body.request, lambda claims: record_denial(request, claims))
        response.headers["Cache-Control"] = "no-store"
        with transaction(request) as engine:
            return engine.evaluate(body.request, token, body.capability_id)

    return router
