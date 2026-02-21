import unittest

from app.services.tick_engine import InMemoryTickEngine


class TickEngineTests(unittest.IsolatedAsyncioTestCase):
    async def test_move_command_completes_with_ticks(self) -> None:
        engine = InMemoryTickEngine(tick_hz=5, width=10, height=10)
        q = await engine.register_listener("a1")
        agent = await engine.ensure_agent("a1")
        self.assertEqual((agent.x, agent.y), (1, 1))

        started = await engine.submit_move_command(
            agent_id="a1",
            server_cmd_id="cmd-1",
            target_x=3,
            target_y=1,
        )
        self.assertEqual(started, 1)

        await engine.tick_once()
        await engine.tick_once()

        # Consume queue until command_result appears.
        result = None
        while not q.empty():
            msg = q.get_nowait()
            if msg["type"] == "command_result":
                result = msg
                break

        self.assertIsNotNone(result)
        self.assertEqual(result["payload"]["status"], "completed")

        delta = await engine.chunk_delta_payload()
        pos = {a["id"]: (a["x"], a["y"]) for a in delta["agents"]}
        self.assertEqual(pos["a1"], (3, 1))

    async def test_move_command_fails_when_blocked(self) -> None:
        engine = InMemoryTickEngine(tick_hz=5, width=10, height=10)
        q1 = await engine.register_listener("a1")
        await engine.register_listener("a2")
        a1 = await engine.ensure_agent("a1")
        a2 = await engine.ensure_agent("a2")

        self.assertEqual((a1.x, a1.y), (1, 1))
        self.assertEqual((a2.x, a2.y), (2, 1))

        await engine.submit_move_command(
            agent_id="a1",
            server_cmd_id="cmd-block",
            target_x=2,
            target_y=1,
        )

        await engine.tick_once()

        result = None
        while not q1.empty():
            msg = q1.get_nowait()
            if msg["type"] == "command_result":
                result = msg
                break

        self.assertIsNotNone(result)
        self.assertEqual(result["payload"]["status"], "failed")
        self.assertEqual(result["payload"]["reason"], "blocked")

        delta = await engine.chunk_delta_payload()
        pos = {a["id"]: (a["x"], a["y"]) for a in delta["agents"]}
        self.assertEqual(pos["a1"], (1, 1))
        self.assertEqual(pos["a2"], (2, 1))


if __name__ == "__main__":
    unittest.main()
