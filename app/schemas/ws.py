from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class WsEnvelope(BaseModel):
    type: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class CommandReqPayload(BaseModel):
    client_cmd_id: str
    cmd: Dict[str, Any]


class CommandAnswerProof(BaseModel):
    proof_nonce: str
    pow_hash: Optional[str] = None


class CommandAnswerPayload(BaseModel):
    server_cmd_id: str
    sig: str
    proof: Optional[CommandAnswerProof] = None


class CommandAckPayload(BaseModel):
    server_cmd_id: str
    accepted: bool
    reason: Optional[str] = None
    echo: Optional[Dict[str, Any]] = None
    started_tick: Optional[int] = None


class CommandResultPayload(BaseModel):
    server_cmd_id: str
    status: Literal["completed", "failed"]
    reason: Optional[str] = None
    ended_tick: int
