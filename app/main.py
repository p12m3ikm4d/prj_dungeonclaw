from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers.http import router as http_router
from app.routers.spectator import router as spectator_router
from app.routers.ws_agent import router as ws_agent_router
from app.services.container import build_container


def _parse_cors_origins(raw: str) -> list[str]:
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


settings = get_settings()
app = FastAPI(title=settings.app_name)
origins = _parse_cors_origins(settings.cors_allow_origins)
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials="*" not in origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.state.settings = settings
app.state.services = build_container(settings)

app.include_router(http_router)
app.include_router(ws_agent_router)
app.include_router(spectator_router)


@app.on_event("startup")
async def on_startup() -> None:
    await app.state.services.tick_engine.start()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await app.state.services.tick_engine.stop()


@app.get("/")
async def root() -> dict:
    return {
        "service": settings.app_name,
        "environment": settings.environment,
    }
