from typing import Literal, Optional

from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class SignupResponse(BaseModel):
    account_id: str
    email: str


class CreateKeyRequest(BaseModel):
    account_id: str
    label: Optional[str] = Field(default=None, max_length=64)


class CreateKeyResponse(BaseModel):
    key_id: str
    key_prefix: str
    api_key: str


class CreateSessionRequest(BaseModel):
    api_key: str
    role: Literal["agent", "spectator"]
    agent_id: Optional[str] = None


class CreateSessionResponse(BaseModel):
    session_token: str
    session_jti: str
    role: Literal["agent", "spectator"]
    cmd_secret: str
    expires_at: int


class DevMoveToRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=128)
    x: int
    y: int


class DevMoveToResponse(BaseModel):
    server_cmd_id: str
    accepted: bool
    reason: Optional[str] = None
    started_tick: Optional[int] = None
