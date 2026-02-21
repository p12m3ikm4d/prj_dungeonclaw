from __future__ import annotations

import asyncio
import json
import secrets
from typing import Any, AsyncIterator, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.services.auth_store import AuthError
from app.services.container import ServiceContainer
from app.services.tick_engine import TickEngineError

router = APIRouter()


def _services(request: Request) -> ServiceContainer:
    return request.app.state.services


def _extract_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("authorization") or ""
    if not auth_header.lower().startswith("bearer "):
        return ""
    return auth_header.split(" ", 1)[1].strip()


def _resolve_chunk_id(request: Request, chunk_id: str) -> str:
    normalized = chunk_id.strip()
    if normalized == "demo":
        return request.app.state.services.tick_engine.default_chunk_id
    return normalized


def _is_dev_test_token(request: Request, token: str) -> bool:
    settings = request.app.state.settings
    return settings.dev_spectator_session_enabled and token == "test-spectator-token"


def _sse_frame(*, event: str, data: Dict[str, Any], event_id: Optional[str] = None) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    lines = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {payload}")
    return "\n".join(lines) + "\n\n"


@router.get("/v1/spectate/stream")
@router.get("/api/v1/spectate/stream", include_in_schema=False)
async def spectate_stream(
    request: Request,
    chunk_id: str = Query(..., min_length=1),
) -> StreamingResponse:
    services = _services(request)
    token = _extract_bearer_token(request)
    resolved_chunk_id = _resolve_chunk_id(request, chunk_id)

    if not _is_dev_test_token(request, token):
        try:
            services.auth_store.validate_session(token=token, role="spectator", agent_id=None)
        except AuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    try:
        bootstrap = await services.tick_engine.open_spectator_feed(
            chunk_id=resolved_chunk_id,
            last_event_id=request.headers.get("last-event-id"),
        )
    except TickEngineError as exc:
        if exc.reason == "chunk_not_found":
            raise HTTPException(status_code=404, detail=exc.reason) from exc
        raise HTTPException(status_code=400, detail=exc.reason) from exc

    queue: asyncio.Queue = bootstrap["queue"]
    stream_chunk_id: str = bootstrap["chunk_id"]
    keepalive = max(5, int(request.app.state.settings.sse_keepalive_seconds))
    channel_id = f"sse-{secrets.token_hex(4)}"

    async def stream() -> AsyncIterator[str]:
        try:
            yield _sse_frame(
                event="session_ready",
                data={
                    "type": "session_ready",
                    "role": "spectator",
                    "chunk_id": stream_chunk_id,
                    "channel_id": channel_id,
                },
            )

            replay_events = bootstrap["replay_events"]
            if bootstrap["resync_required"]:
                yield _sse_frame(
                    event="resync_required",
                    data={
                        "type": "resync_required",
                        "chunk_id": stream_chunk_id,
                        "snapshot_url": f"/v1/chunks/{stream_chunk_id}/snapshot",
                    },
                )
                yield _sse_frame(
                    event="chunk_static",
                    data={
                        "type": "chunk_static",
                        **bootstrap["chunk_static"],
                    },
                )
                yield _sse_frame(
                    event="chunk_delta",
                    data={
                        "type": "chunk_delta",
                        **bootstrap["chunk_delta"],
                    },
                )
            elif replay_events:
                for item in replay_events:
                    yield _sse_frame(
                        event=str(item["event"]),
                        data=dict(item["data"]),
                        event_id=str(item["id"]),
                    )
            else:
                yield _sse_frame(
                    event="chunk_static",
                    data={
                        "type": "chunk_static",
                        **bootstrap["chunk_static"],
                    },
                )
                yield _sse_frame(
                    event="chunk_delta",
                    data={
                        "type": "chunk_delta",
                        **bootstrap["chunk_delta"],
                    },
                )

            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=keepalive)
                except asyncio.TimeoutError:
                    yield _sse_frame(
                        event="heartbeat",
                        data={
                            "type": "heartbeat",
                            "chunk_id": stream_chunk_id,
                            "tick": services.tick_engine.tick,
                        },
                    )
                    continue

                event_name = str(event.get("event", "message"))
                event_data = dict(event.get("data", {}))
                event_id = event.get("id")
                yield _sse_frame(
                    event=event_name,
                    data=event_data,
                    event_id=str(event_id) if event_id else None,
                )
                if event_name == "chunk_closed":
                    break
        finally:
            await services.tick_engine.unregister_spectator_listener(stream_chunk_id, queue)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(stream(), media_type="text/event-stream", headers=headers)


@router.get("/v1/chunks/{chunk_id}/snapshot")
@router.get("/api/v1/chunks/{chunk_id}/snapshot", include_in_schema=False)
async def chunk_snapshot(request: Request, chunk_id: str) -> JSONResponse:
    services = _services(request)
    token = _extract_bearer_token(request)
    resolved_chunk_id = _resolve_chunk_id(request, chunk_id)

    if not _is_dev_test_token(request, token):
        session = services.auth_store.get_session(token)
        if session is None:
            raise HTTPException(status_code=401, detail="invalid_session")
        if session.role not in {"agent", "spectator"}:
            raise HTTPException(status_code=403, detail="invalid_scope")

    try:
        payload = await services.tick_engine.chunk_snapshot_payload(chunk_id=resolved_chunk_id)
    except TickEngineError as exc:
        if exc.reason == "chunk_not_found":
            raise HTTPException(status_code=404, detail=exc.reason) from exc
        raise HTTPException(status_code=400, detail=exc.reason) from exc

    return JSONResponse(payload)
