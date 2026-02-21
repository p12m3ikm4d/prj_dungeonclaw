from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DC_", env_file=".env", extra="ignore")

    app_name: str = "dungeonclaw-backend"
    environment: str = "dev"
    cors_allow_origins: str = "http://localhost:5173"
    enable_dev_spectator_session: bool = True
    session_ttl_seconds: int = 900
    challenge_expires_seconds: int = 5
    challenge_ttl_seconds: int = 10
    challenge_default_difficulty: int = 2
    tick_hz: int = 5
    chunk_width: int = 50
    chunk_height: int = 50
    chunk_gc_ttl_seconds: int = 60

    @property
    def dev_spectator_session_enabled(self) -> bool:
        env = self.environment.lower()
        return self.enable_dev_spectator_session and env not in {"prod", "production"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
