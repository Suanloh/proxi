from alembic import context
from sqlalchemy import text
from sqlalchemy.engine import Connection, URL

from app.config import load_settings
from app.infra.db.database import Database, database_url
from app.infra.db.models import SCHEMA, Base

_CREATE_SCHEMA = f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"


def _url() -> URL:
    url = database_url(load_settings())
    if url is None:
        raise RuntimeError("Configure PROXI_DATABASE_URL or PROXI_TEST_DATABASE_URL for the current environment")
    return url


def _include(name: str | None, type_: str, parent_names: dict[str, str | None]) -> bool:
    return type_ != "schema" or name == SCHEMA


def _run(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        include_schemas=True,
        include_name=_include,
        compare_server_default=True,
        version_table_schema=SCHEMA,
    )
    with context.begin_transaction():
        connection.execute(text(_CREATE_SCHEMA))
        context.run_migrations()


if context.is_offline_mode():
    context.configure(dialect_name=_url().get_backend_name(), version_table_schema=SCHEMA, literal_binds=True)
    with context.begin_transaction():
        context.execute(_CREATE_SCHEMA)
        context.run_migrations()
else:
    supplied = context.config.attributes.get("connection")
    if supplied is not None:
        _run(supplied)
    else:
        database = Database(_url())
        try:
            with database.engine.connect() as connection:
                _run(connection)
        finally:
            database.close()
