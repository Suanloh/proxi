from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


class InvalidCredential(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class CredentialClaims:
    agent_id: UUID
    session_id: UUID
    credential_id: UUID
    issued_at: int
    expires_at: int


class CredentialCodec(Protocol):
    def encode(self, claims: CredentialClaims) -> str: ...
    def decode(self, token: str) -> CredentialClaims: ...
