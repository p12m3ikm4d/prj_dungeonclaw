import secrets
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.schemas.ws import CommandAnswerPayload, CommandReqPayload, WsEnvelope
from app.services.auth_store import AuthError
from app.services.container import ServiceContainer

router = APIRouter()


def _extract_bearer_token(websocket: WebSocket) -> str:
    auth_header = websocket.headers.get("authorization") or ""
    if not auth_header.lower().startswith("bearer "):
        return ""
    return auth_header.split(" ", 1)[1].strip()


async def _send(websocket: WebSocket, message_type: str, payload: Dict[str, Any]) -> None:
    await websocket.send_json({"type": message_type, "payload": payload})


@router.websocket("/v1/agent/ws")
async def agent_ws(websocket: WebSocket, agent_id: str) -> None:
    await websocket.accept()

    services: ServiceContainer = websocket.app.state.services
    token = _extract_bearer_token(websocket)
    channel_id = f"ws-{secrets.token_hex(4)}"

    try:
        session = services.auth_store.validate_session(token=token, role="agent", agent_id=agent_id)
    except AuthError as exc:
        await _send(websocket, "error", {"reason": str(exc)})
        await websocket.close(code=1008)
        return

    pending_commands: Dict[str, Dict[str, Any]] = {}

    await _send(
        websocket,
        "session_ready",
        {
            "agent_id": agent_id,
            "channel_id": channel_id,
            "role": "agent",
        },
    )

    try:
        while True:
            raw = await websocket.receive_json()
            envelope = WsEnvelope.model_validate(raw)

            if envelope.type == "ping":
                await _send(websocket, "heartbeat", {"ok": True})
                continue

            if envelope.type == "command_req":
                req = CommandReqPayload.model_validate(envelope.payload)

                cmd_type = req.cmd.get("type")
                if cmd_type not in {"move_to", "say"}:
                    await _send(
                        websocket,
                        "command_ack",
                        {
                            "server_cmd_id": "",
                            "accepted": False,
                            "reason": "invalid_cmd",
                        },
                    )
                    continue

                temp_server_cmd = f"busy_{agent_id}"
                if not services.auth_store.acquire_agent_lock(agent_id, temp_server_cmd):
                    await _send(
                        websocket,
                        "command_ack",
                        {
                            "server_cmd_id": "",
                            "accepted": False,
                            "reason": "busy",
                        },
                    )
                    continue

                challenge = services.challenge_service.issue(
                    agent_id=agent_id,
                    session_jti=session.jti,
                    channel_id=channel_id,
                    client_cmd_id=req.client_cmd_id,
                    cmd=req.cmd,
                )
                services.auth_store.release_agent_lock(agent_id, temp_server_cmd)
                services.auth_store.acquire_agent_lock(agent_id, challenge.server_cmd_id)

                pending_commands[challenge.server_cmd_id] = {
                    "cmd": req.cmd,
                    "client_cmd_id": req.client_cmd_id,
                }

                await _send(
                    websocket,
                    "command_challenge",
                    {
                        "client_cmd_id": challenge.client_cmd_id,
                        "server_cmd_id": challenge.server_cmd_id,
                        "nonce": challenge.nonce,
                        "expires_at": challenge.expires_at,
                        "difficulty": challenge.difficulty,
                        "channel_id": channel_id,
                        "sig_alg": "HMAC-SHA256",
                        "pow_alg": "sha256-leading-hex-zeroes",
                    },
                )
                continue

            if envelope.type == "command_answer":
                answer = CommandAnswerPayload.model_validate(envelope.payload)
                pending = pending_commands.get(answer.server_cmd_id)
                if pending is None:
                    await _send(
                        websocket,
                        "command_ack",
                        {
                            "server_cmd_id": answer.server_cmd_id,
                            "accepted": False,
                            "reason": "expired_challenge",
                        },
                    )
                    continue

                proof_nonce = answer.proof.proof_nonce if answer.proof else None
                verify = services.challenge_service.verify_answer(
                    server_cmd_id=answer.server_cmd_id,
                    agent_id=agent_id,
                    session_jti=session.jti,
                    channel_id=channel_id,
                    session_cmd_secret=session.cmd_secret,
                    sig=answer.sig,
                    proof_nonce=proof_nonce,
                )

                if not verify.ok:
                    services.auth_store.release_agent_lock(agent_id, answer.server_cmd_id)
                    pending_commands.pop(answer.server_cmd_id, None)
                    await _send(
                        websocket,
                        "command_ack",
                        {
                            "server_cmd_id": answer.server_cmd_id,
                            "accepted": False,
                            "reason": verify.reason,
                        },
                    )
                    continue

                await _send(
                    websocket,
                    "command_ack",
                    {
                        "server_cmd_id": answer.server_cmd_id,
                        "accepted": True,
                        "echo": pending["cmd"],
                        "started_tick": 0,
                    },
                )

                await _send(
                    websocket,
                    "command_result",
                    {
                        "server_cmd_id": answer.server_cmd_id,
                        "status": "completed",
                        "ended_tick": 0,
                    },
                )

                services.auth_store.release_agent_lock(agent_id, answer.server_cmd_id)
                pending_commands.pop(answer.server_cmd_id, None)
                continue

            await _send(websocket, "error", {"reason": "unsupported_message_type"})

    except WebSocketDisconnect:
        for server_cmd_id in list(pending_commands.keys()):
            services.auth_store.release_agent_lock(agent_id, server_cmd_id)
        return
