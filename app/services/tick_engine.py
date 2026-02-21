from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

from app.services.pathfinding import Cell, astar_path


@dataclass
class AgentEntity:
    agent_id: str
    x: int
    y: int


@dataclass
class MoveCommand:
    server_cmd_id: str
    agent_id: str
    target_x: int
    target_y: int
    path: List[Cell]
    accepted_tick: int
    accepted_order: int
    path_index: int = 0


class TickEngineError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class InMemoryTickEngine:
    def __init__(self, tick_hz: int, width: int = 50, height: int = 50) -> None:
        self.tick_hz = tick_hz
        self.width = width
        self.height = height
        self.chunk_id = "chunk-0"
        self.tiles_static = ["." * width for _ in range(height)]

        self._tick = 0
        self._accept_serial = 0
        self._agents: Dict[str, AgentEntity] = {}
        self._occupancy: Dict[Cell, str] = {}
        self._pending: Deque[MoveCommand] = deque()
        self._executing: Dict[str, MoveCommand] = {}
        self._agent_active_cmd: Dict[str, str] = {}

        self._listeners: Dict[str, Set[asyncio.Queue]] = {}

        self._lock = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None

    @property
    def tick(self) -> int:
        return self._tick

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run_loop(self) -> None:
        interval = 1.0 / max(1, self.tick_hz)
        while True:
            started = time.perf_counter()
            await self.tick_once()
            elapsed = time.perf_counter() - started
            await asyncio.sleep(max(0.0, interval - elapsed))

    async def register_listener(self, agent_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._listeners.setdefault(agent_id, set()).add(queue)
        return queue

    async def unregister_listener(self, agent_id: str, queue: asyncio.Queue) -> None:
        async with self._lock:
            listeners = self._listeners.get(agent_id)
            if not listeners:
                return
            listeners.discard(queue)
            if not listeners:
                self._listeners.pop(agent_id, None)

    async def ensure_agent(self, agent_id: str) -> AgentEntity:
        async with self._lock:
            existing = self._agents.get(agent_id)
            if existing:
                return existing

            for y in range(1, self.height - 1):
                for x in range(1, self.width - 1):
                    pos = (x, y)
                    if pos not in self._occupancy:
                        entity = AgentEntity(agent_id=agent_id, x=x, y=y)
                        self._agents[agent_id] = entity
                        self._occupancy[pos] = agent_id
                        return entity

        raise TickEngineError("no_spawn_available")

    async def remove_agent(self, agent_id: str) -> None:
        async with self._lock:
            self._agent_active_cmd.pop(agent_id, None)

            stale_ids = [
                cmd.server_cmd_id for cmd in self._pending if cmd.agent_id == agent_id
            ]
            if stale_ids:
                self._pending = deque(cmd for cmd in self._pending if cmd.agent_id != agent_id)
                for sid in stale_ids:
                    self._executing.pop(sid, None)

            for cmd_id, cmd in list(self._executing.items()):
                if cmd.agent_id == agent_id:
                    self._executing.pop(cmd_id, None)

            entity = self._agents.pop(agent_id, None)
            if entity is not None:
                self._occupancy.pop((entity.x, entity.y), None)

    async def has_active_command(self, agent_id: str) -> bool:
        async with self._lock:
            return agent_id in self._agent_active_cmd

    async def submit_move_command(
        self,
        *,
        agent_id: str,
        server_cmd_id: str,
        target_x: int,
        target_y: int,
    ) -> int:
        async with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                raise TickEngineError("agent_not_found")

            if agent_id in self._agent_active_cmd:
                raise TickEngineError("busy")

            if not (0 <= target_x < self.width and 0 <= target_y < self.height):
                raise TickEngineError("out_of_bounds")

            start = (agent.x, agent.y)
            goal = (target_x, target_y)

            def is_blocked(cell: Cell) -> bool:
                occ = self._occupancy.get(cell)
                if occ is None:
                    return False
                return occ != agent_id

            path = astar_path(
                width=self.width,
                height=self.height,
                start=start,
                goal=goal,
                is_blocked=is_blocked,
            )
            if path is None:
                raise TickEngineError("unreachable")

            self._accept_serial += 1
            accepted_tick = self._tick + 1
            cmd = MoveCommand(
                server_cmd_id=server_cmd_id,
                agent_id=agent_id,
                target_x=target_x,
                target_y=target_y,
                path=path,
                accepted_tick=accepted_tick,
                accepted_order=self._accept_serial,
            )
            self._pending.append(cmd)
            self._agent_active_cmd[agent_id] = server_cmd_id
            return accepted_tick

    def _emit_to_agent(self, agent_id: str, message: Dict[str, Any]) -> None:
        listeners = self._listeners.get(agent_id, set())
        for queue in listeners:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                pass

    def _emit_to_all(self, message: Dict[str, Any]) -> None:
        for agent_id in list(self._listeners.keys()):
            self._emit_to_agent(agent_id, message)

    def _agent_snapshots(self) -> List[Dict[str, Any]]:
        agents = [
            {"id": entity.agent_id, "x": entity.x, "y": entity.y}
            for entity in self._agents.values()
        ]
        agents.sort(key=lambda item: item["id"])
        return agents

    async def chunk_static_payload(self) -> Dict[str, Any]:
        async with self._lock:
            return {
                "chunk_id": self.chunk_id,
                "size": {"w": self.width, "h": self.height},
                "tiles": list(self.tiles_static),
                "legend": {".": "floor"},
                "neighbors": {"N": None, "E": None, "S": None, "W": None},
                "tick_base": self._tick,
            }

    async def chunk_delta_payload(self) -> Dict[str, Any]:
        async with self._lock:
            return {
                "chunk_id": self.chunk_id,
                "tick": self._tick,
                "agents": self._agent_snapshots(),
                "events": [],
            }

    async def tick_once(self) -> None:
        async with self._lock:
            self._tick += 1

            while self._pending and self._pending[0].accepted_tick <= self._tick:
                cmd = self._pending.popleft()
                self._executing[cmd.server_cmd_id] = cmd

            moved = False
            blocked_events: List[Dict[str, Any]] = []
            finished_cmds: List[Tuple[MoveCommand, str, Optional[Dict[str, Any]]]] = []

            running = sorted(
                self._executing.values(),
                key=lambda c: (c.accepted_tick, c.accepted_order, c.agent_id),
            )

            for cmd in running:
                agent = self._agents.get(cmd.agent_id)
                if agent is None:
                    finished_cmds.append((cmd, "failed", {"reason": "agent_not_found"}))
                    continue

                if cmd.path_index >= len(cmd.path):
                    finished_cmds.append((cmd, "completed", None))
                    continue

                next_x, next_y = cmd.path[cmd.path_index]
                occupant = self._occupancy.get((next_x, next_y))
                if occupant is not None and occupant != cmd.agent_id:
                    meta = {
                        "reason": "blocked",
                        "blocked_at": {"x": next_x, "y": next_y},
                        "blocker": {"id": occupant, "x": next_x, "y": next_y},
                    }
                    blocked_events.append(
                        {
                            "type": "blocked",
                            "by": occupant,
                            "at": {"x": next_x, "y": next_y},
                        }
                    )
                    finished_cmds.append((cmd, "failed", meta))
                    continue

                old_pos = (agent.x, agent.y)
                self._occupancy.pop(old_pos, None)
                self._occupancy[(next_x, next_y)] = cmd.agent_id
                agent.x = next_x
                agent.y = next_y
                cmd.path_index += 1
                moved = True

                if cmd.path_index >= len(cmd.path):
                    finished_cmds.append((cmd, "completed", None))

            for cmd, status, meta in finished_cmds:
                self._executing.pop(cmd.server_cmd_id, None)
                self._agent_active_cmd.pop(cmd.agent_id, None)

                payload: Dict[str, Any] = {
                    "server_cmd_id": cmd.server_cmd_id,
                    "status": status,
                    "ended_tick": self._tick,
                }
                if meta:
                    payload.update(meta)
                self._emit_to_agent(cmd.agent_id, {"type": "command_result", "payload": payload})

            if moved or blocked_events:
                delta = {
                    "chunk_id": self.chunk_id,
                    "tick": self._tick,
                    "agents": self._agent_snapshots(),
                    "events": blocked_events,
                }
                self._emit_to_all({"type": "chunk_delta", "payload": delta})
