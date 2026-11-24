import re
from typing import Annotated
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, StringConstraints

from .authz import Decision

_HOST = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?")
_PATH = re.compile(r"/[a-zA-Z0-9._~/-]*")


def normalize_page(value: str) -> str:
    if not value.isascii() or any(ord(char) <= 32 or ord(char) == 127 for char in value):
        raise ValueError("Invalid browser URL")
    if any(char in value for char in "?%#\\@"):
        raise ValueError("Browser URL must not contain credentials, escapes, queries or fragments")
    url = urlsplit(value)
    host, port = url.hostname, url.port
    path = url.path or "/"
    loopback = host == "127.0.0.1"
    if (host is None or (not loopback and not _HOST.fullmatch(host))
            or url.scheme not in ({"http", "https"} if loopback else {"https"})
            or port == 0 or url.netloc.lower() != (f"{host}:{port}" if port is not None else host)
            or not _PATH.fullmatch(path) or any(part in {".", ".."} for part in path.split("/"))):
        raise ValueError("Invalid browser URL")
    authority = host if port is None or port == (443 if url.scheme == "https" else 80) else f"{host}:{port}"
    return urlunsplit((url.scheme, authority, path, "", ""))


PageURL = Annotated[str, StringConstraints(min_length=1, max_length=255), AfterValidator(normalize_page)]
BrowserOperation = Annotated[str, StringConstraints(max_length=96, pattern=r"^browser\.[a-z][a-z0-9_]*$")]


class BrowserAction(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    request_id: UUID
    agent_id: UUID
    session_id: UUID
    task_id: UUID
    capability_id: UUID | None = None
    action: BrowserOperation
    url: PageURL
    timestamp: AwareDatetime


class PageResult(BaseModel):
    url: PageURL
    title: str
    text: str | None = None
    truncated: bool = False


class BrowserResponse(BaseModel):
    decision: Decision
    executed: bool
    approval_id: UUID | None = None
    result: PageResult | None = None
