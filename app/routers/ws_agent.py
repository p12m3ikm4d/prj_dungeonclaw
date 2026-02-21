import asyncio
import secrets
from typing import Any, Dict, Tuple

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.schemas.ws import CommandAnswerPayload, CommandReqPayload, WsEnvelope
from app.services.auth_store import AuthError
from app.services.container import ServiceContainer
from app.services.tick_engine import TickEngineError

router = APIRouter()


def _extract_bearer_token(websocket: WebSocket) -> str:
    auth_header = websocket.headers.get("authorization") or ""
    if not auth_header.lower().startswith("bearer "):
        return ""
    return auth_header.split(" ", 1)[1].strip()


async def _send(websocket: WebSocket, message_type: str, payload: Dict[str, Any]) -> None:
    await websocket.send_json({"type": message_type, "payload": payload})


async def _wait_for_client_or_engine(
    websocket: WebSocket,
    event_queue: asyncio.Queue,
) -> Tuple[str, Dict[str, Any]]:
    recv_task = asyncio.create_task(websocket.receive_json())
    event_task = asyncio.create_task(event_queue.get())
    done, pending = await asyncio.wait({recv_task, event_task}, return_when=asyncio.FIRST_COMPLETED)

    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)

    if recv_task in done:
        return "client", recv_task.result()
    return "engine", event_task.result()


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

    await services.tick_engine.ensure_agent(agent_id)
    event_queue = await services.tick_engine.register_listener(agent_id)

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
    await _send(
        websocket,
        "chunk_static",
        await services.tick_engine.chunk_static_payload(agent_id=agent_id),
    )
    await _send(
        websocket,
        "chunk_delta",
        await services.tick_engine.chunk_delta_payload(agent_id=agent_id),
    )

    try:
        while True:
            source, raw = await _wait_for_client_or_engine(websocket, event_queue)
            if source == "engine":
                await websocket.send_json(raw)
                continue

            envelope = WsEnvelope.model_validate(raw)

            if envelope.type == "ping":
                await _send(websocket, "heartbeat", {"ok": True})
                continue

            if envelope.type == "command_req":
                req = CommandReqPayload.model_validate(envelope.payload)

                if pending_commands:
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

                if await services.tick_engine.has_active_command(agent_id):
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

                challenge = services.challenge_service.issue(
                    agent_id=agent_id,
                    session_jti=session.jti,
                    channel_id=channel_id,
                    client_cmd_id=req.client_cmd_id,
                    cmd=req.cmd,
                )

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

                cmd_payload = pending["cmd"]
                if cmd_payload.get("type") == "say":
                    await _send(
                        websocket,
                        "command_ack",
                        {
                            "server_cmd_id": answer.server_cmd_id,
                            "accepted": True,
                            "echo": cmd_payload,
                            "started_tick": services.tick_engine.tick,
                        },
                    )
                    await _send(
                        websocket,
                        "command_result",
                        {
                            "server_cmd_id": answer.server_cmd_id,
                            "status": "completed",
                            "ended_tick": services.tick_engine.tick,
                        },
                    )
                    pending_commands.pop(answer.server_cmd_id, None)
                    continue

                try:
                    started_tick = await services.tick_engine.submit_move_command(
                        agent_id=agent_id,
                        server_cmd_id=answer.server_cmd_id,
                        target_x=int(cmd_payload.get("x", -1)),
                        target_y=int(cmd_payload.get("y", -1)),
                    )
                except (ValueError, TypeError):
                    pending_commands.pop(answer.server_cmd_id, None)
                    await _send(
                        websocket,
                        "command_ack",
                        {
                            "server_cmd_id": answer.server_cmd_id,
                            "accepted": False,
                            "reason": "invalid_cmd",
                        },
                    )
                    continue
                except TickEngineError as exc:
                    pending_commands.pop(answer.server_cmd_id, None)
                    await _send(
                        websocket,
                        "command_ack",
                        {
                            "server_cmd_id": answer.server_cmd_id,
                            "accepted": False,
                            "reason": exc.reason,
                        },
                    )
                    continue

                await _send(
                    websocket,
                    "command_ack",
                    {
                        "server_cmd_id": answer.server_cmd_id,
                        "accepted": True,
                        "echo": cmd_payload,
                        "started_tick": started_tick,
                    },
                )

                pending_commands.pop(answer.server_cmd_id, None)
                continue

            await _send(websocket, "error", {"reason": "unsupported_message_type"})

    except WebSocketDisconnect:
        return
    finally:
        await services.tick_engine.unregister_listener(agent_id, event_queue)
        await services.tick_engine.remove_agent(agent_id)
