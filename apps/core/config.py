from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SKDO API"
    database_url: str = "sqlite+pysqlite:///./skdo.db"
    schema_version: str = "v1"
    s3_endpoint_url: Optional[str] = None
    s3_access_key_id: Optional[str] = None
    s3_secret_access_key: Optional[str] = None
    s3_bucket: str = "skdo"
    media_storage_path: str = "storage"

    model_config = SettingsConfigDict(env_prefix="SKDO_", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
