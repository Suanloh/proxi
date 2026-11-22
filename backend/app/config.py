import os
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PROXI_", env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True,
    )

    env: Literal["development", "testing"] = "development"
    log_level: LogLevel = "INFO"
    database_url: SecretStr | None = None
    test_database_url: SecretStr | None = None
    dev_identity_owner_id: UUID | None = None
    dev_identity_token: Annotated[SecretStr, Field(min_length=32)] | None = None


class TestingSettings(Settings):
    log_level: LogLevel = "WARNING"


def load_settings() -> Settings:
    env = os.getenv("PROXI_ENV", "development")
    if env == "development":
        return Settings(env=env, _env_file=Path(__file__).resolve().parents[2] / ".env")
    if env == "testing":
        return TestingSettings(env=env, _env_file=None)
    raise ValueError("PROXI_ENV must be development or testing")
