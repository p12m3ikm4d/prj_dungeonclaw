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

    async def test_boundary_transition_emits_transition_then_static_then_delta(self) -> None:
        engine = InMemoryTickEngine(tick_hz=5, width=6, height=6)
        q = await engine.register_listener("a1")
        await engine.ensure_agent("a1")

        await engine.submit_move_command(
            agent_id="a1",
            server_cmd_id="cmd-transition",
            target_x=5,
            target_y=1,
        )

        for _ in range(5):
            await engine.tick_once()

        events = []
        while not q.empty():
            events.append(q.get_nowait())

        transition_idx = None
        for idx, event in enumerate(events):
            if event["type"] == "chunk_transition":
                transition_idx = idx
                break

        self.assertIsNotNone(transition_idx)
        assert transition_idx is not None
        self.assertGreaterEqual(len(events), transition_idx + 3)
        self.assertEqual(events[transition_idx + 1]["type"], "chunk_static")
        self.assertEqual(events[transition_idx + 2]["type"], "chunk_delta")

        transition = events[transition_idx]["payload"]
        self.assertEqual(transition["from_chunk_id"], "chunk-0")
        self.assertNotEqual(transition["to_chunk_id"], "chunk-0")
        self.assertEqual(transition["to"], {"x": 0, "y": 1})

        state = await engine.agent_state("a1")
        self.assertIsNotNone(state)
        assert state is not None
        self.assertEqual(state.chunk_id, transition["to_chunk_id"])
        self.assertEqual((state.x, state.y), (0, 1))

    async def test_transition_blocked_by_destination_occupancy_keeps_origin_position(self) -> None:
        engine = InMemoryTickEngine(tick_hz=5, width=6, height=6)
        q1 = await engine.register_listener("a1")
        await engine.register_listener("a2")
        await engine.ensure_agent("a1")
        await engine.ensure_agent("a2")

        await engine.submit_move_command(
            agent_id="a2",
            server_cmd_id="cmd-a2-transition",
            target_x=5,
            target_y=1,
        )
        for _ in range(4):
            await engine.tick_once()

        await engine.submit_move_command(
            agent_id="a1",
            server_cmd_id="cmd-a1-blocked-transition",
            target_x=5,
            target_y=1,
        )
        for _ in range(6):
            await engine.tick_once()

        result = None
        while not q1.empty():
            event = q1.get_nowait()
            if (
                event["type"] == "command_result"
                and event["payload"]["server_cmd_id"] == "cmd-a1-blocked-transition"
            ):
                result = event
                break

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["payload"]["status"], "failed")
        self.assertEqual(result["payload"]["reason"], "blocked")

        state = await engine.agent_state("a1")
        self.assertIsNotNone(state)
        assert state is not None
        self.assertEqual(state.chunk_id, "chunk-0")
        self.assertEqual((state.x, state.y), (4, 1))

    async def test_gc_removes_inactive_leaf_chunk_and_recreates_on_reentry(self) -> None:
        now = [1_700_000_000.0]
        engine = InMemoryTickEngine(
            tick_hz=5,
            width=6,
            height=6,
            chunk_gc_ttl_seconds=10,
            clock=lambda: now[0],
        )
        q = await engine.register_listener("a1")
        await engine.ensure_agent("a1")

        await engine.submit_move_command(
            agent_id="a1",
            server_cmd_id="cmd-first-transition",
            target_x=5,
            target_y=1,
        )
        for _ in range(5):
            await engine.tick_once()

        first_chunk_id = None
        while not q.empty():
            event = q.get_nowait()
            if event["type"] == "chunk_transition":
                first_chunk_id = event["payload"]["to_chunk_id"]
                break

        self.assertIsNotNone(first_chunk_id)
        assert first_chunk_id is not None
        self.assertTrue(await engine.has_chunk(first_chunk_id))

        await engine.remove_agent("a1")
        now[0] += 30
        await engine.tick_once()
        self.assertFalse(await engine.has_chunk(first_chunk_id))

        await engine.ensure_agent("a1")
        await engine.submit_move_command(
            agent_id="a1",
            server_cmd_id="cmd-second-transition",
            target_x=5,
            target_y=1,
        )
        for _ in range(5):
            await engine.tick_once()

        second_chunk_id = None
        while not q.empty():
            event = q.get_nowait()
            if event["type"] == "chunk_transition":
                second_chunk_id = event["payload"]["to_chunk_id"]

        self.assertIsNotNone(second_chunk_id)
        assert second_chunk_id is not None
        self.assertNotEqual(first_chunk_id, second_chunk_id)
        self.assertTrue(await engine.has_chunk(second_chunk_id))


if __name__ == "__main__":
    unittest.main()
