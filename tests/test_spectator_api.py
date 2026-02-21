import json
import unittest

from fastapi.testclient import TestClient

from app.main import app


def _collect_sse_events(response, limit: int):
    events = []
    event_name = None
    event_id = None
    data_lines = []

    for raw in response.iter_lines():
        line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        if line == "":
            if data_lines:
                payload = json.loads("\n".join(data_lines))
                events.append({"event": event_name, "id": event_id, "data": payload})
                if len(events) >= limit:
                    break
            event_name = None
            event_id = None
            data_lines = []
            continue

        if line.startswith("event: "):
            event_name = line[len("event: ") :]
            continue
        if line.startswith("id: "):
            event_id = line[len("id: ") :]
            continue
        if line.startswith("data: "):
            data_lines.append(line[len("data: ") :])

    return events


class SpectatorApiTests(unittest.TestCase):
    def test_spectate_stream_requires_spectator_token(self) -> None:
        with TestClient(app) as client:
            response = client.get("/v1/spectate/stream?chunk_id=chunk-0")
            self.assertEqual(response.status_code, 401)

    def test_spectator_stream_and_snapshot_endpoints(self) -> None:
        with TestClient(app) as client:
            session = client.post("/v1/dev/spectator-session")
            self.assertEqual(session.status_code, 200)
            token = session.json()["session_token"]
            headers = {"authorization": f"Bearer {token}"}

            with client.stream("GET", "/v1/spectate/stream?chunk_id=chunk-0", headers=headers) as response:
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/event-stream", response.headers.get("content-type", ""))
                events = _collect_sse_events(response, limit=3)

            self.assertGreaterEqual(len(events), 3)
            self.assertEqual(events[0]["event"], "session_ready")
            self.assertEqual(events[1]["event"], "chunk_static")
            self.assertEqual(events[2]["event"], "chunk_delta")
            self.assertEqual(events[1]["data"]["chunk_id"], "chunk-0")

            snapshot = client.get("/v1/chunks/chunk-0/snapshot", headers=headers)
            self.assertEqual(snapshot.status_code, 200)
            snap_payload = snapshot.json()
            self.assertIn("chunk_static", snap_payload)
            self.assertIn("latest_delta", snap_payload)

            legacy_snapshot = client.get("/api/v1/chunks/chunk-0/snapshot", headers=headers)
            self.assertEqual(legacy_snapshot.status_code, 200)


if __name__ == "__main__":
    unittest.main()
