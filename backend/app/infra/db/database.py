from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import Session, sessionmaker

from ...config import Settings


def database_url(settings: Settings) -> URL | None:
    secret = settings.test_database_url if settings.env == "testing" else settings.database_url
    if secret is None:
        return None
    try:
        url = make_url(secret.get_secret_value())
    except (ArgumentError, ValueError):
        raise ValueError("Invalid PostgreSQL database URL") from None
    if url.drivername != "postgresql+psycopg" or not (url.host and url.database and url.username):
        raise ValueError("Expected a postgresql+psycopg URL with host, user and database")
    if settings.env == "testing":
        if url.host not in {"127.0.0.1", "::1"} or not url.port or url.query:
            raise ValueError("Test PostgreSQL URL must use a literal loopback address, explicit port and no options")
        if not (url.database == "postgres" or url.database.startswith("proxi_test_")):
            raise ValueError("Test PostgreSQL URL must name postgres or a proxi_test_ database")
        url = url.update_query_dict({"hostaddr": url.host})
    return url


class Database:
    def __init__(self, url: URL) -> None:
        self.engine = create_engine(url, pool_pre_ping=True, hide_parameters=True)
        self._sessions = sessionmaker(self.engine, expire_on_commit=False)

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        with self._sessions.begin() as session:
            yield session

    def close(self) -> None:
        self.engine.dispose()
