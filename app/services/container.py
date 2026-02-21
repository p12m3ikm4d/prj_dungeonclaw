from dataclasses import dataclass

from app.config import Settings
from app.services.auth_store import InMemoryAuthStore
from app.services.challenge_service import ChallengeService


@dataclass
class ServiceContainer:
    auth_store: InMemoryAuthStore
    challenge_service: ChallengeService


def build_container(settings: Settings) -> ServiceContainer:
    return ServiceContainer(
        auth_store=InMemoryAuthStore(session_ttl_seconds=settings.session_ttl_seconds),
        challenge_service=ChallengeService(
            challenge_expires_seconds=settings.challenge_expires_seconds,
            challenge_ttl_seconds=settings.challenge_ttl_seconds,
            default_difficulty=settings.challenge_default_difficulty,
        ),
    )
