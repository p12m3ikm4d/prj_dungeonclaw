from fastapi import FastAPI

from app.config import get_settings
from app.routers.http import router as http_router
from app.routers.ws_agent import router as ws_agent_router
from app.services.container import build_container

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.state.services = build_container(settings)

app.include_router(http_router)
app.include_router(ws_agent_router)


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
