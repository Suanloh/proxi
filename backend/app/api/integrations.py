from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..core.creds.tokens import CredentialClaims, CredentialCodec
from ..schs.authz import ActionRequest
from ..schs.integrations import ToolRequest, ToolResponse
from ..svcs.authz import AuthorizationEngine
from ..svcs.enforcement import EnforcementController
from ..svcs.integrations import SUPPORTED_TOOLS, IntegrationExecutionError, IntegrationRegistry, ToolSpec, tool_restriction
from .authz import bound_agent_token


def create_integration_router(
    registry: IntegrationRegistry, codec: CredentialCodec | None,
    transaction: Callable[[Request], AbstractContextManager[AuthorizationEngine]],
    record_denial: Callable[[Request, CredentialClaims | None], None],
) -> APIRouter:
    router = APIRouter(tags=["integrations"])
    bearer = HTTPBearer(auto_error=False, scheme_name="AgentBearer", bearerFormat="JWT")

    def endpoint(spec: ToolSpec) -> Callable[..., ToolResponse]:
        def execute(
            body: ToolRequest, request: Request, response: Response,
            credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
        ) -> ToolResponse:
            action = ActionRequest(
                request_id=body.request_id, agent_id=body.agent_id, session_id=body.session_id,
                task_id=body.task_id, timestamp=body.timestamp.astimezone(UTC), resource=body.resource,
                action=spec.action, integration_type=spec.kind,
            )
            token = bound_agent_token(credentials, codec, action, lambda claims: record_denial(request, claims))
            response.headers["Cache-Control"] = "no-store"
            with registry.dispatch(spec) as (adapter, enabled):
                controller = EnforcementController(
                    lambda: transaction(request), lambda _: None, {(spec.kind, spec.action): adapter.execute},
                    restriction=lambda normalized: tool_restriction(spec, enabled, normalized),
                )
                try:
                    result = controller.enforce(action, token, body.capability_id)
                except IntegrationExecutionError:
                    raise HTTPException(status_code=502, headers={"Cache-Control": "no-store"}) from None
            return ToolResponse(decision=result.decision, executed=result.executed,
                                approval_id=result.approval_id, result=result.result)

        return execute

    for spec in SUPPORTED_TOOLS:
        router.add_api_route(spec.path, endpoint(spec), methods=["POST"], name=spec.action)
    return router
