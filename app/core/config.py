"""Settings: config/base.yaml -> config/{APP_ENV}.yaml -> environment variables (env wins).

Owner: Soughat
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        out[key] = _deep_merge(out[key], value) if isinstance(value, dict) and isinstance(out.get(key), dict) else value
    return out


def load_yaml_config(env: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for name in ("base.yaml", f"{env}.yaml"):
        path = CONFIG_DIR / name
        if path.exists():
            data = _deep_merge(data, yaml.safe_load(path.read_text()) or {})
    return data


class Settings(BaseSettings):
    """Secrets and connection strings come from the environment only."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    secret_key: str
    field_encryption_key: str = ""
    mongodb_uri: str = "mongodb://localhost:27017/?replicaSet=rs0"
    mongodb_db: str = "lendwise"
    redis_url: str = "redis://localhost:6379/0"
    s3_endpoint_url: str | None = None
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "lendwise-documents"
    s3_region: str = "ap-south-1"
    cors_origins: str = "http://localhost:5173"
    sentry_dsn: str = ""

    @property
    def yaml(self) -> dict[str, Any]:
        return load_yaml_config(self.app_env)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings(app_env=os.getenv("APP_ENV", "development"))  # type: ignore[call-arg]
