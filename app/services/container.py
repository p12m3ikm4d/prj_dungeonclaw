from dataclasses import dataclass

from app.config import Settings
from app.services.auth_store import InMemoryAuthStore
from app.services.challenge_service import ChallengeService
from app.services.tick_engine import InMemoryTickEngine


@dataclass
class ServiceContainer:
    auth_store: InMemoryAuthStore
    challenge_service: ChallengeService
    tick_engine: InMemoryTickEngine


def build_container(settings: Settings) -> ServiceContainer:
    return ServiceContainer(
        auth_store=InMemoryAuthStore(session_ttl_seconds=settings.session_ttl_seconds),
        challenge_service=ChallengeService(
            challenge_expires_seconds=settings.challenge_expires_seconds,
            challenge_ttl_seconds=settings.challenge_ttl_seconds,
            default_difficulty=settings.challenge_default_difficulty,
        ),
        tick_engine=InMemoryTickEngine(
            tick_hz=settings.tick_hz,
            width=settings.chunk_width,
            height=settings.chunk_height,
            chunk_gc_ttl_seconds=settings.chunk_gc_ttl_seconds,
        ),
    )
