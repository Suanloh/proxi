from collections.abc import Callable
from secrets import compare_digest
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import SecretStr


def bearer_required() -> HTTPException:
    return HTTPException(status_code=401, headers={"WWW-Authenticate": "Bearer"})


def create_owner_auth(owner_id: UUID | None, token: SecretStr | None) -> Callable[..., UUID]:
    bearer = HTTPBearer(auto_error=False, scheme_name="OwnerBearer")
    expected = token.get_secret_value().encode("utf-8") if token is not None else None

    def authenticate(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> UUID:
        if owner_id is None or expected is None:
            raise HTTPException(status_code=503)
        if credentials is None or not compare_digest(credentials.credentials.encode("utf-8"), expected):
            raise bearer_required()
        return owner_id

    return authenticate
