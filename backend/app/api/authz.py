from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..core.creds.tokens import CredentialCodec, InvalidCredential
from ..schs.authz import AuthorizationCheck, Decision
from ..svcs.authz import AuthorizationEngine
from .owner_auth import bearer_required


def create_authorization_router(
    codec: CredentialCodec | None,
    transaction: Callable[[Request], AbstractContextManager[AuthorizationEngine]],
) -> APIRouter:
    router = APIRouter(prefix="/authorization", tags=["authorization"])
    bearer = HTTPBearer(auto_error=False, scheme_name="AgentBearer", bearerFormat="JWT")

    @router.post("/check")
    def check(
        body: AuthorizationCheck, request: Request, response: Response,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> Decision:
        if credentials is None or len(credentials.credentials) > 2048:
            raise bearer_required()
        if codec is None:
            raise HTTPException(status_code=503)
        token = credentials.credentials
        try:
            claims = codec.decode(token)
        except InvalidCredential:
            raise bearer_required() from None
        if (claims.agent_id, claims.session_id) != (body.request.agent_id, body.request.session_id):
            raise bearer_required()
        response.headers["Cache-Control"] = "no-store"
        with transaction(request) as engine:
            return engine.evaluate(body.request, token, body.capability_id)

    return router
