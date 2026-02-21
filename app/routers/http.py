from fastapi import APIRouter, HTTPException, Request

from app.schemas.auth import (
    CreateKeyRequest,
    CreateKeyResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    SignupRequest,
    SignupResponse,
)
from app.services.auth_store import AuthError
from app.services.container import ServiceContainer

router = APIRouter()


def _services(request: Request) -> ServiceContainer:
    return request.app.state.services


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
