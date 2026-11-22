from collections.abc import Iterator
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import delete, inspect, text
from sqlalchemy.exc import IntegrityError

from app.config import Settings, load_settings
from app.infra.db.database import Database, database_url
from app.infra.db.models import AgentRow
from app.infra.repos.sqlalchemy import mutable_repository, repository
from app.main import create_app
from app.models import records as r


@pytest.fixture
def database() -> Iterator[Database]:
    url = database_url(Settings(env="testing"))
    if url is None:
        pytest.skip("Set PROXI_TEST_DATABASE_URL to run PostgreSQL integration tests")
    admin = Database(url)
    name = f"proxi_test_{uuid4().hex}"
    try:
        with admin.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text(f"CREATE DATABASE {name}"))
        db = Database(url.set(database=name))
        try:
            yield db
        finally:
            db.close()
            with admin.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                connection.execute(text(f"DROP DATABASE {name}"))
    finally:
        admin.close()


def migrate(database: Database, action: str, revision: str) -> None:
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    with database.engine.connect() as connection:
        config.attributes["connection"] = connection
        (command.upgrade if action == "upgrade" else command.downgrade)(config, revision)


@pytest.fixture
def migrated(database: Database) -> Database:
    migrate(database, "upgrade", "head")
    return database


def test_app_lifecycle_uses_configured_database(database: Database) -> None:
    url = database.engine.url.difference_update_query(["hostaddr"])
    app = create_app(Settings(env="testing", test_database_url=SecretStr(url.render_as_string(hide_password=False))))
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200
        db = app.state.database
        with db.transaction() as session:
            assert session.scalar(text("SELECT current_database()")) == url.database
        assert not inspect(db.engine).has_schema("proxi")
        pool = db.engine.pool
    assert db.engine.pool is not pool


def test_migration_round_trip(database: Database) -> None:
    migrate(database, "upgrade", "head")
    migrate(database, "downgrade", "base")
    assert set(inspect(database.engine).get_table_names(schema="proxi")) <= {"alembic_version"}
    migrate(database, "upgrade", "head")
    with database.engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM proxi.alembic_version")) == "0001"


def test_repositories_round_trip_all_records(migrated: Database) -> None:
    expires = datetime.now(timezone(timedelta(hours=8))) + timedelta(days=1)
    user = r.User(email="owner@example.test")
    agent = r.Agent(owner_id=user.id, name="Example")
    session = r.AgentSession(agent_id=agent.id, expires_at=expires)
    task = r.Task(agent_id=agent.id, objective="Read a document")
    policy = r.Policy(owner_id=user.id, name="Default")
    version = r.PolicyVersion(policy_id=policy.id, version=1, status="active")
    action = r.ActionRequest(session_id=session.id, task_id=task.id, action="read", resource="document")
    decision = r.AuthorizationDecision(
        action_request_id=action.id, outcome="HOLD", reason_code="review", policy_version_id=version.id,
    )
    approval = r.ApprovalRequest(decision_id=decision.id, expires_at=expires)
    records = (
        user, agent, session,
        r.Credential(agent_id=agent.id, secret_ref="vault:test-reference"),
        r.Capability(agent_id=agent.id, action="read", resource="document", expires_at=expires),
        task, r.IntentInterpretation(task_id=task.id, interpreter="test", summary="Read only"),
        policy, version, r.PolicyRule(policy_version_id=version.id, position=0, action="read",
                                      resource="document", outcome="HOLD"),
        action, decision, approval,
        r.ApprovalRecord(approval_request_id=approval.id, reviewer_id=user.id, outcome="approved"),
        r.BehaviourEvent(agent_id=agent.id, event_type="observed"),
        r.TrustScore(agent_id=agent.id, score=50),
        r.TrustEvent(agent_id=agent.id, delta=-5, reason_code="example"),
        r.AuditLog(agent_id=agent.id, action_request_id=action.id, event_type="decision"),
        r.SecurityEvent(agent_id=agent.id, event_type="observed", severity="info"),
        r.IntegrationConnection(agent_id=agent.id, kind="browser", name="Example"),
    )
    with migrated.transaction() as db:
        saved = [repository(db, type(record)).add(record) for record in records]
    with migrated.transaction() as db:
        for original, stored in zip(records, saved, strict=True):
            assert stored.created_at is not None and stored.created_at.tzinfo is timezone.utc
            assert stored.updated_at == stored.created_at
            assert stored == replace(original, created_at=stored.created_at, updated_at=stored.updated_at)
            assert repository(db, type(stored)).get(stored.id) == stored
        stored_session = repository(db, r.AgentSession).get(session.id)
        assert stored_session is not None and stored_session.expires_at.tzinfo is timezone.utc

    with migrated.transaction() as db:
        agents = mutable_repository(db, r.Agent)
        disabled = agents.update(replace(agent, status="disabled"))
        assert disabled.created_at is not None and disabled.updated_at is not None
        assert disabled.updated_at > disabled.created_at
        sessions = mutable_repository(db, r.AgentSession)
        revoked = sessions.update(replace(session, revoked_at=datetime.now(timezone.utc)))
        assert revoked.revoked_at is not None
    with migrated.transaction() as db:
        assert repository(db, r.AgentSession).get(session.id) == revoked


def test_foreign_keys_rollback_and_audit_retention(migrated: Database) -> None:
    user = r.User(email="history@example.test")
    with pytest.raises(IntegrityError) as orphan, migrated.transaction() as db:
        repository(db, r.User).add(user)
        repository(db, r.Agent).add(r.Agent(owner_id=uuid4(), name="Orphan"))
    assert isinstance(orphan.value.orig, psycopg.IntegrityError)
    assert orphan.value.orig.diag.constraint_name == "fk_agents_owner_id"

    with migrated.transaction() as db:
        assert repository(db, r.User).get(user.id) is None
        repository(db, r.User).add(user)
        agent = repository(db, r.Agent).add(r.Agent(owner_id=user.id, name="Historical"))
        log = repository(db, r.AuditLog).add(r.AuditLog(agent_id=agent.id, event_type="recorded"))

    with pytest.raises(IntegrityError) as deletion, migrated.transaction() as db:
        db.execute(delete(AgentRow).where(AgentRow.id == agent.id))
    assert isinstance(deletion.value.orig, psycopg.IntegrityError)
    assert deletion.value.orig.diag.constraint_name == "fk_audit_logs_agent_id"
    with migrated.transaction() as db:
        assert repository(db, r.AuditLog).get(log.id) == log
        with pytest.raises(ValueError, match="append-only"):
            mutable_repository(db, r.AuditLog)


def test_policy_replacement_keeps_previous_version(migrated: Database) -> None:
    with migrated.transaction() as db:
        user = repository(db, r.User).add(r.User(email="policy@example.test"))
        policy = repository(db, r.Policy).add(r.Policy(owner_id=user.id, name="Versioned"))
        versions = mutable_repository(db, r.PolicyVersion)
        old = versions.add(r.PolicyVersion(policy_id=policy.id, version=1, status="active"))
    new = r.PolicyVersion(policy_id=policy.id, version=2, status="active")
    with pytest.raises(IntegrityError) as conflict, migrated.transaction() as db:
        repository(db, r.PolicyVersion).add(new)
    assert isinstance(conflict.value.orig, psycopg.IntegrityError)
    assert conflict.value.orig.diag.constraint_name == "uq_policy_versions_active"
    with migrated.transaction() as db:
        versions = mutable_repository(db, r.PolicyVersion)
        superseded = versions.update(replace(old, status="superseded", superseded_at=datetime.now(timezone.utc)))
        versions.add(new)
    with migrated.transaction() as db:
        assert repository(db, r.PolicyVersion).get(old.id) == superseded


def test_testing_does_not_use_development_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROXI_ENV", "testing")
    monkeypatch.setenv("PROXI_DATABASE_URL", "postgresql+psycopg://example@remote.example.test/dev")
    monkeypatch.delenv("PROXI_TEST_DATABASE_URL", raising=False)
    assert database_url(load_settings()) is None
    for url in (
        "postgresql+psycopg://example@remote.example.test:5432/postgres",
        "postgresql+psycopg://example@127.0.0.1:5432/postgres?hostaddr=192.0.2.1",
        "postgresql+psycopg://example@127.0.0.1:5432/proxi_dev",
    ):
        with pytest.raises(ValueError, match="Test PostgreSQL URL"):
            database_url(Settings(env="testing", test_database_url=SecretStr(url)))