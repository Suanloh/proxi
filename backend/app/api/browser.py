from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..core.creds.tokens import CredentialClaims, CredentialCodec
from ..integrations.browser.playwright import SUPPORTED_ACTIONS, BrowserExecutionError, PlaywrightBrowser
from ..models.records import AgentType
from ..schs.authz import ActionRequest
from ..schs.browser import BrowserAction, BrowserResponse
from ..svcs.authz import AuthorizationEngine
from ..svcs.enforcement import EnforcementController
from .authz import bound_agent_token


def create_browser_router(
    browser: PlaywrightBrowser, codec: CredentialCodec | None,
    transaction: Callable[[Request], AbstractContextManager[AuthorizationEngine]],
    record_denial: Callable[[Request, CredentialClaims | None], None],
) -> APIRouter:
    router = APIRouter(prefix="/browser", tags=["browser"])
    bearer = HTTPBearer(auto_error=False, scheme_name="AgentBearer", bearerFormat="JWT")
    adapters = {(AgentType.BROWSER, action): browser.render for action in SUPPORTED_ACTIONS}

    @router.post("/actions")
    def execute(
        body: BrowserAction, request: Request, response: Response,
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> BrowserResponse:
        action = ActionRequest(
            request_id=body.request_id, agent_id=body.agent_id, session_id=body.session_id, task_id=body.task_id,
            action=body.action, resource=body.url, timestamp=body.timestamp.astimezone(UTC),
            integration_type=AgentType.BROWSER,
        )
        token = bound_agent_token(credentials, codec, action, lambda claims: record_denial(request, claims))
        controller = EnforcementController(lambda: transaction(request), lambda _: None,
                                           adapters, restriction=browser.restriction)
        response.headers["Cache-Control"] = "no-store"
        try:
            result = controller.enforce(action, token, body.capability_id)
        except BrowserExecutionError:
            raise HTTPException(status_code=502, headers={"Cache-Control": "no-store"}) from None
        return BrowserResponse(decision=result.decision, executed=result.executed,
                               approval_id=result.approval_id, result=result.result)

    return router
