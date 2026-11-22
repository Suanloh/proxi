from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app import config
from app.config import Settings, load_settings
from app.main import create_app


def test_health_is_versioned() -> None:
    with TestClient(create_app(Settings(env="testing"))) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        unversioned = client.get("/health")
        assert unversioned.status_code == 404
        assert unversioned.json() == {"error": {"code": "http_error", "message": "Not Found"}}


def test_validation_error_does_not_echo_request_input() -> None:
    app = create_app(Settings(env="testing"))

    @app.get("/items/{item_id}")
    async def get_item(item_id: int) -> int:
        return item_id

    with TestClient(app) as client:
        response = client.get("/items/private-input")

    assert response.status_code == 422
    assert response.json() == {"error": {"code": "validation_error", "message": "Invalid request"}}


def test_unexpected_error_does_not_expose_exception_details() -> None:
    app = create_app(Settings(env="testing"))

    @app.get("/failure")
    async def failure() -> None:
        raise RuntimeError("private diagnostic detail")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/failure")

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "Internal server error"},
    }


def test_development_dotenv_is_isolated_from_testing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "__file__", str(tmp_path / "backend" / "app" / "config.py"))
    (tmp_path / ".env").write_text("PROXI_ENV=testing\nPROXI_LOG_LEVEL=DEBUG\n", encoding="utf-8")
    monkeypatch.delenv("PROXI_LOG_LEVEL", raising=False)
    monkeypatch.delenv("PROXI_ENV", raising=False)
    settings = load_settings()
    assert (settings.env, settings.log_level) == ("development", "DEBUG")
    monkeypatch.setenv("PROXI_LOG_LEVEL", "ERROR")
    assert load_settings().log_level == "ERROR"
    monkeypatch.delenv("PROXI_LOG_LEVEL")
    monkeypatch.setenv("PROXI_ENV", "testing")
    settings = load_settings()
    assert (settings.env, settings.log_level) == ("testing", "WARNING")


def test_agent_management_requires_explicit_opt_in_and_bearer() -> None:
    settings = Settings(env="testing", dev_identity_owner_id=uuid4(), dev_identity_token=None)
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/agents").status_code == 503

    settings = Settings(env="testing", dev_identity_owner_id=uuid4(), dev_identity_token=SecretStr(uuid4().hex))
    with TestClient(create_app(settings)) as client:
        for headers in ({}, {"Authorization": "Bearer invalid"}):
            response = client.get("/api/v1/agents", headers=headers)
            assert response.status_code == 401
            assert response.headers["WWW-Authenticate"] == "Bearer"


def test_invalid_environment_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROXI_ENV", "staging")
    with pytest.raises(ValueError, match="development.*testing"):
        load_settings()
