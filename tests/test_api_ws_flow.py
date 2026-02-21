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


class ApiWsFlowTests(unittest.TestCase):
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
                delta_msg = ws.receive_json()
                self.assertEqual(delta_msg["type"], "chunk_delta")

                cmd = {"type": "move_to", "x": 2, "y": 1}
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
