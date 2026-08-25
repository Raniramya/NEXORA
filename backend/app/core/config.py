from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # Resolve the environment file from the repository root so API, migrations,
    # tests, and standalone workers all receive the same configuration regardless
    # of their current working directory.
    model_config = SettingsConfigDict(
        env_prefix="NEXORA_",
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str = "postgresql+psycopg://nexora:nexora@localhost:5432/nexora_cdi"
    cors_origins: str = "http://localhost:3000"
    log_level: str = "INFO"
    storage_path: str = "../storage"
    edge_ingest_token: str | None = None
    api_url: str = "http://localhost:8000"
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_topic: str = "nexora/machines/+/signal-windows"
    mqtt_client_id: str = "nexora-edge-bridge"
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_tls: bool = False
    mqtt_ca_file: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
