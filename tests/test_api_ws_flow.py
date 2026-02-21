import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.services.challenge_service import ChallengeService


def _find_pow_nonce(nonce: str, cmd_hash: str, difficulty: int) -> str:
    probe = 0
    while True:
        ok, _ = ChallengeService.verify_pow(nonce, cmd_hash, str(probe), difficulty)
        if ok:
            return str(probe)
        probe += 1


def _pick_target_from_stream(static_payload: dict, delta_payload: dict, agent_id: str) -> tuple[int, int]:
    grid = static_payload["payload"]["grid"]
    me = None
    for item in delta_payload["payload"]["agents"]:
        if item["id"] == agent_id:
            me = item
            break
    if me is None:
        raise AssertionError("agent_not_found_in_delta")

    width = len(grid[0])
    height = len(grid)
    x0 = int(me["x"])
    y0 = int(me["y"])
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)):
        x = x0 + dx
        y = y0 + dy
        if not (0 <= x < width and 0 <= y < height):
            continue
        if grid[y][x] == 0:
            return x, y

    for y in range(height):
        for x in range(width):
            if grid[y][x] == 0 and (x, y) != (x0, y0):
                return x, y
    raise AssertionError("no_walkable_target")


class ApiWsFlowTests(unittest.TestCase):
    def test_dev_spectator_session_and_cors_preflight(self) -> None:
        with TestClient(app) as client:
            preflight = client.options(
                "/healthz",
                headers={
                    "Origin": "http://localhost:5173",
                    "Access-Control-Request-Method": "GET",
                },
            )
            self.assertIn(preflight.status_code, (200, 204))
            self.assertEqual(
                preflight.headers.get("access-control-allow-origin"),
                "http://localhost:5173",
            )

            dev_session = client.post("/v1/dev/spectator-session")
            self.assertEqual(dev_session.status_code, 200)
            payload = dev_session.json()
            self.assertEqual(payload["role"], "spectator")
            self.assertTrue(payload["session_token"].startswith("sess_"))
            self.assertTrue(payload["session_jti"].startswith("jti_"))

    def test_dev_spectator_session_can_be_disabled(self) -> None:
        original = app.state.settings.enable_dev_spectator_session
        app.state.settings.enable_dev_spectator_session = False
        try:
            with TestClient(app) as client:
                response = client.post("/v1/dev/spectator-session")
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["detail"], "dev_spectator_session_disabled")
        finally:
            app.state.settings.enable_dev_spectator_session = original

    def test_dev_agent_move_to_without_challenge(self) -> None:
        with TestClient(app) as client:
            target_x = app.state.settings.chunk_width // 2
            target_y = app.state.settings.chunk_height // 2
            response = client.post(
                "/v1/dev/agent/move-to",
                headers={"authorization": "Bearer test-spectator-token"},
                json={"agent_id": "debug-agent-a", "x": target_x, "y": target_y},
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertTrue(payload["accepted"])
            self.assertTrue(payload["server_cmd_id"].startswith("dev-"))
            self.assertGreaterEqual(payload["started_tick"], 1)

    def test_dev_agent_move_to_legacy_alias(self) -> None:
        with TestClient(app) as client:
            target_x = app.state.settings.chunk_width // 2
            target_y = app.state.settings.chunk_height // 2
            response = client.post(
                "/api/v1/dev/agent/move-to",
                headers={"authorization": "Bearer test-spectator-token"},
                json={"agent_id": "debug-agent-b", "x": target_x, "y": target_y},
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertIn("accepted", payload)

    def test_dev_agent_move_to_rejects_without_auth(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/v1/dev/agent/move-to",
                json={"agent_id": "debug-agent-c", "x": 3, "y": 1},
            )
            self.assertEqual(response.status_code, 401)

    def test_signup_to_ws_handshake_flow(self) -> None:
        with TestClient(app) as client:
            signup = client.post(
                "/v1/signup",
                json={"email": "agent@example.com", "password": "password123"},
            )
            self.assertEqual(signup.status_code, 200)
            account_id = signup.json()["account_id"]

            key = client.post(
                "/v1/keys",
                json={"account_id": account_id, "label": "dev"},
            )
            self.assertEqual(key.status_code, 200)
            api_key = key.json()["api_key"]

            session = client.post(
                "/v1/sessions",
                json={
                    "api_key": api_key,
                    "role": "agent",
                    "agent_id": "agent-1",
                },
            )
            self.assertEqual(session.status_code, 200)
            session_token = session.json()["session_token"]
            cmd_secret = session.json()["cmd_secret"]
            session_jti = session.json()["session_jti"]

            headers = {"authorization": f"Bearer {session_token}"}
            with client.websocket_connect("/v1/agent/ws?agent_id=agent-1", headers=headers) as ws:
                ready = ws.receive_json()
                self.assertEqual(ready["type"], "session_ready")
                _channel_id = ready["payload"]["channel_id"]

                static_msg = ws.receive_json()
                self.assertEqual(static_msg["type"], "chunk_static")
                self.assertEqual(
                    static_msg["payload"]["render_hint"]["npc_overlay"],
                    "chunk_delta.npcs",
                )
                self.assertEqual(
                    static_msg["payload"]["render_hint"]["debug_move_default_agent_id"],
                    "demo-player",
                )
                delta_msg = ws.receive_json()
                self.assertEqual(delta_msg["type"], "chunk_delta")
                self.assertIn("npcs", delta_msg["payload"])
                self.assertTrue(
                    any(str(item["id"]).startswith("demo-npc-") for item in delta_msg["payload"]["npcs"])
                )

                target_x, target_y = _pick_target_from_stream(static_msg, delta_msg, "agent-1")
                cmd = {"type": "move_to", "x": target_x, "y": target_y}
                ws.send_json(
                    {
                        "type": "command_req",
                        "payload": {
                            "client_cmd_id": "c-1",
                            "cmd": cmd,
                        },
                    }
                )

                challenge = ws.receive_json()
                self.assertEqual(challenge["type"], "command_challenge")
                payload = challenge["payload"]

                cmd_hash = ChallengeService.hash_cmd(cmd)
                sig_payload = ChallengeService.build_sig_payload(
                    session_jti=session_jti,
                    channel_id=payload["channel_id"],
                    agent_id="agent-1",
                    server_cmd_id=payload["server_cmd_id"],
                    client_cmd_id=payload["client_cmd_id"],
                    cmd_hash=cmd_hash,
                    nonce=payload["nonce"],
                    expires_at=payload["expires_at"],
                    difficulty=payload["difficulty"],
                )
                sig = ChallengeService.sign(cmd_secret, sig_payload)
                proof_nonce = _find_pow_nonce(payload["nonce"], cmd_hash, payload["difficulty"])

                ws.send_json(
                    {
                        "type": "command_answer",
                        "payload": {
                            "server_cmd_id": payload["server_cmd_id"],
                            "sig": sig,
                            "proof": {
                                "proof_nonce": proof_nonce,
                            },
                        },
                    }
                )

                ack = ws.receive_json()
                self.assertEqual(ack["type"], "command_ack")
                self.assertTrue(ack["payload"]["accepted"])
                self.assertGreaterEqual(ack["payload"]["started_tick"], 1)

                seen_result = None
                for _ in range(10):
                    event = ws.receive_json()
                    if event["type"] == "command_result":
                        seen_result = event
                        break
                self.assertIsNotNone(seen_result)
                self.assertEqual(seen_result["payload"]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
