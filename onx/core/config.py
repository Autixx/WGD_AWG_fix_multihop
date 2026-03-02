import base64
import hashlib
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ONX API"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    debug: bool = False
    database_url: str = Field(
        default=f"sqlite:///{(Path(__file__).resolve().parents[2] / 'onx_dev.db').as_posix()}",
    )
    master_key: str = "onx-dev-master-key-change-me"
    ssh_connect_timeout_seconds: int = 10

    model_config = SettingsConfigDict(
        env_prefix="ONX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def get_fernet_key() -> bytes:
    digest = hashlib.sha256(get_settings().master_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)
