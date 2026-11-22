from uuid import UUID

import jwt
from pydantic import SecretStr

from ...core.creds.tokens import CredentialClaims, InvalidCredential

_ISSUER = "proxi"
_AUDIENCE = "proxi-agent-access"
_ALGORITHM = "HS256"


class JwtCredentialCodec:
    def __init__(self, signing_key: SecretStr) -> None:
        self._key = bytes.fromhex(signing_key.get_secret_value())
        if len(self._key) != 32:
            raise ValueError("Credential signing key must be 32 bytes")

    def encode(self, claims: CredentialClaims) -> str:
        return jwt.encode({
            "iss": _ISSUER, "aud": _AUDIENCE, "sub": str(claims.agent_id),
            "sid": str(claims.session_id), "jti": str(claims.credential_id),
            "iat": claims.issued_at, "exp": claims.expires_at,
        }, self._key, algorithm=_ALGORITHM)

    def decode(self, token: str) -> CredentialClaims:
        try:
            payload = jwt.decode(token, self._key, algorithms=[_ALGORITHM], issuer=_ISSUER, audience=_AUDIENCE,
                                 options={"strict_aud": True, "require": [
                                     "iss", "aud", "sub", "sid", "jti", "iat", "exp",
                                 ]})
            issued, expires, session = payload["iat"], payload["exp"], payload["sid"]
            if type(issued) is not int or type(expires) is not int or issued >= expires or not isinstance(session, str):
                raise ValueError("Invalid JWT claims")
            return CredentialClaims(UUID(payload["sub"]), UUID(session), UUID(payload["jti"]), issued, expires)
        except (jwt.InvalidTokenError, ValueError, TypeError, OverflowError):
            raise InvalidCredential("Invalid agent credential") from None
