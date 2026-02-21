import unittest
import uuid

from fastapi.testclient import TestClient

from app.main import app


class SpectatorApiTests(unittest.TestCase):
    def test_spectate_stream_requires_spectator_token(self) -> None:
        with TestClient(app) as client:
            response = client.get("/v1/spectate/stream?chunk_id=chunk-0")
            self.assertEqual(response.status_code, 401)

    def test_spectate_stream_demo_alias_route_exists(self) -> None:
        with TestClient(app) as client:
            response = client.get("/api/v1/spectate/stream?chunk_id=demo")
            self.assertEqual(response.status_code, 401)

    def test_snapshot_endpoints_with_spectator_token(self) -> None:
        with TestClient(app) as client:
            session = client.post("/v1/dev/spectator-session")
            self.assertEqual(session.status_code, 200)
            token = session.json()["session_token"]
            headers = {"authorization": f"Bearer {token}"}

            snapshot = client.get("/v1/chunks/chunk-0/snapshot", headers=headers)
            self.assertEqual(snapshot.status_code, 200)
            snap_payload = snapshot.json()
            self.assertIn("chunk_static", snap_payload)
            self.assertIn("latest_delta", snap_payload)
            chunk_static = snap_payload["chunk_static"]
            self.assertIn("grid", chunk_static)
            self.assertIn("render_hint", chunk_static)
            self.assertEqual(chunk_static["render_hint"]["cell_codes"], {"0": "floor", "1": "wall"})
            self.assertEqual(chunk_static["render_hint"]["npc_overlay"], "chunk_delta.npcs")
            self.assertEqual(chunk_static["render_hint"]["debug_move_default_agent_id"], "demo-player")
            self.assertIn("agents", snap_payload["latest_delta"])
            self.assertIn("npcs", snap_payload["latest_delta"])
            center_x = chunk_static["size"]["w"] // 2
            center_y = chunk_static["size"]["h"] // 2
            demo_player = None
            for item in snap_payload["latest_delta"]["agents"]:
                if item["id"] == "demo-player":
                    demo_player = item
                    break
            self.assertIsNotNone(demo_player)
            assert demo_player is not None
            self.assertEqual((demo_player["x"], demo_player["y"]), (center_x, center_y))
            demo_users = [
                item
                for item in snap_payload["latest_delta"]["agents"]
                if str(item["id"]).startswith("demo-user-")
            ]
            demo_npcs = [
                item
                for item in snap_payload["latest_delta"]["npcs"]
                if str(item["id"]).startswith("demo-npc-")
            ]
            self.assertGreaterEqual(len(demo_users), 2)
            self.assertGreaterEqual(len(demo_npcs), 2)
            for item in demo_users + demo_npcs:
                self.assertEqual(chunk_static["grid"][item["y"]][item["x"]], 0)

            legacy_snapshot = client.get("/api/v1/chunks/chunk-0/snapshot", headers=headers)
            self.assertEqual(legacy_snapshot.status_code, 200)

    def test_demo_chunk_alias_returns_default_chunk_snapshot(self) -> None:
        with TestClient(app) as client:
            session = client.post("/v1/dev/spectator-session")
            self.assertEqual(session.status_code, 200)
            token = session.json()["session_token"]
            headers = {"authorization": f"Bearer {token}"}

            snapshot = client.get("/v1/chunks/demo/snapshot", headers=headers)
            self.assertEqual(snapshot.status_code, 200)
            payload = snapshot.json()
            self.assertEqual(payload["chunk_static"]["chunk_id"], "chunk-0")

    def test_owner_stream_requires_owner_token(self) -> None:
        with TestClient(app) as client:
            response = client.get("/v1/owner/stream?agent_id=demo-player")
            self.assertEqual(response.status_code, 401)

    def test_snapshot_endpoints_with_owner_session(self) -> None:
        with TestClient(app) as client:
            email = f"owner-snap-{uuid.uuid4().hex[:8]}@example.com"
            signup = client.post("/v1/signup", json={"email": email, "password": "password123"})
            self.assertEqual(signup.status_code, 200)
            account_id = signup.json()["account_id"]

            key = client.post("/v1/keys", json={"account_id": account_id, "label": "owner"})
            self.assertEqual(key.status_code, 200)
            api_key = key.json()["api_key"]

            session = client.post(
                "/v1/sessions",
                json={
                    "api_key": api_key,
                    "role": "owner_spectator",
                    "agent_id": "demo-player",
                },
            )
            self.assertEqual(session.status_code, 200)
            token = session.json()["session_token"]

            snapshot = client.get(
                "/v1/chunks/chunk-0/snapshot",
                headers={"authorization": f"Bearer {token}"},
            )
            self.assertEqual(snapshot.status_code, 200)


if __name__ == "__main__":
    unittest.main()
