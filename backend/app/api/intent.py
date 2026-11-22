from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from ..core.identity.lifecycle import InvalidAgentStatus
from ..schs.intent import IntentProposalResponse, IntentRequest
from ..svcs.identity import AgentNotFound, OwnerNotAuthorized
from ..svcs.intent import IntentFailure, IntentFailureCode, IntentInterpreter, IntentReview

_FAILURE_STATUS = {
    IntentFailureCode.NOT_CONFIGURED: 503,
    IntentFailureCode.PROVIDER_ERROR: 502,
    IntentFailureCode.TIMEOUT: 504,
    IntentFailureCode.INVALID_OUTPUT: 502,
}


def create_intent_router(
    authenticate_owner: Callable[..., UUID],
    transaction: Callable[[Request], AbstractContextManager[IntentReview]],
    interpreter: IntentInterpreter,
) -> APIRouter:
    router = APIRouter(prefix="/agents/{agent_id}/intent-interpretations", tags=["intent"])
    Owner = Annotated[UUID, Depends(authenticate_owner)]

    @contextmanager
    def review_transaction(request: Request) -> Iterator[IntentReview]:
        try:
            with transaction(request) as review:
                yield review
        except OwnerNotAuthorized:
            raise HTTPException(status_code=403) from None
        except AgentNotFound:
            raise HTTPException(status_code=404) from None
        except InvalidAgentStatus:
            raise HTTPException(status_code=409) from None

    @router.post("", status_code=201)
    async def propose(request: Request, agent_id: UUID, body: IntentRequest, owner: Owner) -> IntentProposalResponse:
        def check_owner() -> None:
            with review_transaction(request) as review:
                review.require_active_agent(owner, agent_id)

        await run_in_threadpool(check_owner)
        try:
            outcome = await interpreter.interpret(body.task)
        except IntentFailure as exc:
            def record_failure(failure: IntentFailureCode) -> None:
                with review_transaction(request) as review:
                    review.record_failure(owner, agent_id, body.task, interpreter.name, failure)

            await run_in_threadpool(record_failure, exc.code)
            raise HTTPException(status_code=_FAILURE_STATUS[exc.code]) from None

        def record_proposal() -> IntentProposalResponse:
            with review_transaction(request) as review:
                return review.record_proposal(owner, agent_id, body.task, interpreter.name, outcome)

        return await run_in_threadpool(record_proposal)

    @router.get("/{interpretation_id}")
    def get_proposal(request: Request, agent_id: UUID, interpretation_id: UUID, owner: Owner) -> IntentProposalResponse:
        with review_transaction(request) as review:
            proposal = review.get_proposal(owner, agent_id, interpretation_id)
        if proposal is None:
            raise HTTPException(status_code=404)
        return proposal

    return router
