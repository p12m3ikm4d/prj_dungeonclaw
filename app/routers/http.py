import secrets

from fastapi import APIRouter, HTTPException, Request

from app.schemas.auth import (
    CreateKeyRequest,
    CreateKeyResponse,
    DevMoveToRequest,
    DevMoveToResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    SignupRequest,
    SignupResponse,
)
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


def _is_dev_test_token(request: Request, token: str) -> bool:
    return request.app.state.settings.dev_spectator_session_enabled and token == "test-spectator-token"


@router.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@router.post("/v1/signup", response_model=SignupResponse)
async def signup(payload: SignupRequest, request: Request) -> SignupResponse:
    try:
        account = _services(request).auth_store.create_account(payload.email, payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return SignupResponse(account_id=account.id, email=account.email)


@router.post("/v1/keys", response_model=CreateKeyResponse)
async def create_key(payload: CreateKeyRequest, request: Request) -> CreateKeyResponse:
    try:
        key, raw = _services(request).auth_store.create_api_key(payload.account_id, payload.label)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CreateKeyResponse(key_id=key.id, key_prefix=key.key_prefix, api_key=raw)


@router.post("/v1/sessions", response_model=CreateSessionResponse)
async def create_session(payload: CreateSessionRequest, request: Request) -> CreateSessionResponse:
    try:
        session = _services(request).auth_store.create_session(
            payload.api_key,
            payload.role,
            payload.agent_id,
        )
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CreateSessionResponse(
        session_token=session.token,
        session_jti=session.jti,
        role=session.role,
        cmd_secret=session.cmd_secret,
        expires_at=session.expires_at,
    )


@router.post("/v1/dev/spectator-session", response_model=CreateSessionResponse)
async def create_dev_spectator_session(request: Request) -> CreateSessionResponse:
    settings = request.app.state.settings
    if not settings.dev_spectator_session_enabled:
        raise HTTPException(status_code=403, detail="dev_spectator_session_disabled")

    session = _services(request).auth_store.create_dev_spectator_session()
    return CreateSessionResponse(
        session_token=session.token,
        session_jti=session.jti,
        role=session.role,
        cmd_secret=session.cmd_secret,
        expires_at=session.expires_at,
    )


@router.post("/v1/dev/agent/move-to", response_model=DevMoveToResponse)
@router.post("/api/v1/dev/agent/move-to", response_model=DevMoveToResponse, include_in_schema=False)
async def dev_agent_move_to(payload: DevMoveToRequest, request: Request) -> DevMoveToResponse:
    settings = request.app.state.settings
    if not settings.dev_spectator_session_enabled:
        raise HTTPException(status_code=403, detail="dev_debug_route_disabled")

    token = _extract_bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="invalid_session")

    if not _is_dev_test_token(request, token):
        session = _services(request).auth_store.get_session(token)
        if session is None:
            raise HTTPException(status_code=401, detail="invalid_session")
        if session.role not in {"agent", "spectator"}:
            raise HTTPException(status_code=403, detail="invalid_scope")

    try:
        await _services(request).tick_engine.ensure_agent(payload.agent_id)
        server_cmd_id = f"dev-{secrets.token_hex(8)}"
        started_tick = await _services(request).tick_engine.submit_move_command(
            agent_id=payload.agent_id,
            server_cmd_id=server_cmd_id,
            target_x=payload.x,
            target_y=payload.y,
        )
    except TickEngineError as exc:
        return DevMoveToResponse(
            server_cmd_id="",
            accepted=False,
            reason=exc.reason,
            started_tick=None,
        )

    return DevMoveToResponse(
        server_cmd_id=server_cmd_id,
        accepted=True,
        reason=None,
        started_tick=started_tick,
    )
