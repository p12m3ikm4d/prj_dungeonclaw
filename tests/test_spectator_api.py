import unittest

from fastapi.testclient import TestClient

from app.main import app


class SpectatorApiTests(unittest.TestCase):
    def test_spectate_stream_requires_spectator_token(self) -> None:
        with TestClient(app) as client:
            response = client.get("/v1/spectate/stream?chunk_id=chunk-0")
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

            legacy_snapshot = client.get("/api/v1/chunks/chunk-0/snapshot", headers=headers)
            self.assertEqual(legacy_snapshot.status_code, 200)


if __name__ == "__main__":
    unittest.main()
