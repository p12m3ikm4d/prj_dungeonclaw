from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DC_", env_file=".env", extra="ignore")

    app_name: str = "dungeonclaw-backend"
    environment: str = "dev"
    session_ttl_seconds: int = 900
    challenge_expires_seconds: int = 5
    challenge_ttl_seconds: int = 10
    challenge_default_difficulty: int = 2


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
