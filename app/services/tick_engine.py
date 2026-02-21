from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Deque, Dict, List, Optional, Set, Tuple

from app.services.pathfinding import Cell, astar_path


@dataclass
class AgentEntity:
    agent_id: str
    chunk_id: str
    x: int
    y: int


@dataclass
class ChunkState:
    chunk_id: str
    width: int
    height: int
    tiles_static: List[str]
    neighbors: Dict[str, Optional[str]]
    occupancy: Dict[Cell, str]
    agents: Set[str]
    created_at: float
    last_player_left_at: Optional[float]
    pinned: bool
    seed: int
    transition_lock_count: int = 0


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
    DIRECTIONS = ("N", "E", "S", "W")
    OPPOSITE_DIR = {"N": "S", "E": "W", "S": "N", "W": "E"}

    def __init__(
        self,
        tick_hz: int,
        width: int = 50,
        height: int = 50,
        chunk_gc_ttl_seconds: int = 60,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self.tick_hz = tick_hz
        self.width = width
        self.height = height
        self.chunk_gc_ttl_seconds = chunk_gc_ttl_seconds
        self._clock = clock or time.time

        self._tick = 0
        self._accept_serial = 0
        self._chunk_serial = 0
        self._agents: Dict[str, AgentEntity] = {}
        self._pending: Deque[MoveCommand] = deque()
        self._executing: Dict[str, MoveCommand] = {}
        self._agent_active_cmd: Dict[str, str] = {}
        self._neighbor_lock_refcnt: Dict[Tuple[str, str], int] = {}

        self._listeners: Dict[str, Set[asyncio.Queue]] = {}

        root = self._new_chunk("chunk-0", pinned=True)
        self._root_chunk_id = root.chunk_id
        self._chunks: Dict[str, ChunkState] = {root.chunk_id: root}

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

            chunk = self._chunks[self._root_chunk_id]
            for y in range(1, self.height - 1):
                for x in range(1, self.width - 1):
                    pos = (x, y)
                    if pos not in chunk.occupancy:
                        entity = AgentEntity(
                            agent_id=agent_id,
                            chunk_id=chunk.chunk_id,
                            x=x,
                            y=y,
                        )
                        self._agents[agent_id] = entity
                        chunk.occupancy[pos] = agent_id
                        chunk.agents.add(agent_id)
                        chunk.last_player_left_at = None
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
                chunk = self._chunks.get(entity.chunk_id)
                if chunk is not None:
                    chunk.occupancy.pop((entity.x, entity.y), None)
                    chunk.agents.discard(agent_id)
                    if not chunk.agents:
                        chunk.last_player_left_at = self._clock()

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

            chunk = self._chunks.get(agent.chunk_id)
            if chunk is None:
                raise TickEngineError("chunk_not_found")

            start = (agent.x, agent.y)
            goal = (target_x, target_y)

            def is_blocked(cell: Cell) -> bool:
                occ = chunk.occupancy.get(cell)
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

    def _agent_snapshots(self, chunk: ChunkState) -> List[Dict[str, Any]]:
        agents = [
            {
                "id": entity.agent_id,
                "x": entity.x,
                "y": entity.y,
            }
            for entity in self._agents.values()
            if entity.chunk_id == chunk.chunk_id
        ]
        agents.sort(key=lambda item: item["id"])
        return agents

    async def chunk_static_payload(
        self,
        *,
        chunk_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        async with self._lock:
            chunk = self._resolve_chunk(chunk_id=chunk_id, agent_id=agent_id)
            return {
                "chunk_id": chunk.chunk_id,
                "size": {"w": self.width, "h": self.height},
                "tiles": list(chunk.tiles_static),
                "legend": {".": "floor"},
                "neighbors": dict(chunk.neighbors),
                "tick_base": self._tick,
            }

    async def chunk_delta_payload(
        self,
        *,
        chunk_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        events: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        async with self._lock:
            chunk = self._resolve_chunk(chunk_id=chunk_id, agent_id=agent_id)
            return {
                "chunk_id": chunk.chunk_id,
                "tick": self._tick,
                "agents": self._agent_snapshots(chunk),
                "events": list(events or []),
            }

    async def tick_once(self) -> None:
        async with self._lock:
            self._tick += 1

            while self._pending and self._pending[0].accepted_tick <= self._tick:
                cmd = self._pending.popleft()
                self._executing[cmd.server_cmd_id] = cmd

            affected_chunks: Set[str] = set()
            chunk_events: Dict[str, List[Dict[str, Any]]] = {}
            transitions: List[Tuple[str, Dict[str, Any], str]] = []
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
                chunk = self._chunks.get(agent.chunk_id)
                if chunk is None:
                    finished_cmds.append((cmd, "failed", {"reason": "chunk_not_found"}))
                    continue

                if cmd.path_index >= len(cmd.path):
                    finished_cmds.append((cmd, "completed", None))
                    continue

                next_x, next_y = cmd.path[cmd.path_index]
                transition_dir = self._boundary_direction(
                    current=(agent.x, agent.y),
                    nxt=(next_x, next_y),
                )
                if transition_dir is not None:
                    outcome = self._attempt_boundary_transition(
                        cmd=cmd,
                        agent=agent,
                        source_chunk=chunk,
                        direction=transition_dir,
                        boundary_cell=(next_x, next_y),
                    )
                    if not outcome["ok"]:
                        blocker_id = str(outcome["blocker"]["id"])
                        at = {
                            "x": int(outcome["blocked_at"]["x"]),
                            "y": int(outcome["blocked_at"]["y"]),
                        }
                        meta = {
                            "reason": "blocked",
                            "blocked_at": at,
                            "blocker": {
                                "id": blocker_id,
                                "x": at["x"],
                                "y": at["y"],
                            },
                        }
                        chunk_events.setdefault(chunk.chunk_id, []).append(
                            {
                                "type": "blocked",
                                "by": blocker_id,
                                "at": at,
                            }
                        )
                        affected_chunks.add(chunk.chunk_id)
                        finished_cmds.append((cmd, "failed", meta))
                        continue

                    from_chunk_id = str(outcome["from_chunk_id"])
                    to_chunk_id = str(outcome["to_chunk_id"])
                    transitions.append(
                        (
                            cmd.agent_id,
                            {
                                "agent_id": cmd.agent_id,
                                "from_chunk_id": from_chunk_id,
                                "to_chunk_id": to_chunk_id,
                                "from": {
                                    "x": int(outcome["from"]["x"]),
                                    "y": int(outcome["from"]["y"]),
                                },
                                "to": {
                                    "x": int(outcome["to"]["x"]),
                                    "y": int(outcome["to"]["y"]),
                                },
                                "tick": self._tick,
                            },
                            to_chunk_id,
                        )
                    )
                    affected_chunks.add(from_chunk_id)
                    affected_chunks.add(to_chunk_id)
                    if cmd.path_index >= len(cmd.path):
                        finished_cmds.append((cmd, "completed", None))
                    continue

                occupant = chunk.occupancy.get((next_x, next_y))
                if occupant is not None and occupant != cmd.agent_id:
                    meta = {
                        "reason": "blocked",
                        "blocked_at": {"x": next_x, "y": next_y},
                        "blocker": {"id": occupant, "x": next_x, "y": next_y},
                    }
                    chunk_events.setdefault(chunk.chunk_id, []).append(
                        {
                            "type": "blocked",
                            "by": occupant,
                            "at": {"x": next_x, "y": next_y},
                        }
                    )
                    affected_chunks.add(chunk.chunk_id)
                    finished_cmds.append((cmd, "failed", meta))
                    continue

                old_pos = (agent.x, agent.y)
                chunk.occupancy.pop(old_pos, None)
                chunk.occupancy[(next_x, next_y)] = cmd.agent_id
                agent.x = next_x
                agent.y = next_y
                cmd.path_index += 1
                affected_chunks.add(chunk.chunk_id)

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

            for agent_id, transition_payload, to_chunk_id in transitions:
                self._emit_to_agent(
                    agent_id,
                    {"type": "chunk_transition", "payload": transition_payload},
                )
                static_payload = self._build_chunk_static_payload(self._chunks[to_chunk_id])
                self._emit_to_agent(
                    agent_id,
                    {"type": "chunk_static", "payload": static_payload},
                )

            for chunk_id in sorted(affected_chunks):
                chunk = self._chunks.get(chunk_id)
                if chunk is None:
                    continue
                self._emit_chunk_delta(
                    chunk,
                    events=chunk_events.get(chunk_id, []),
                )

            self._run_chunk_gc(now=self._clock())

    async def has_chunk(self, chunk_id: str) -> bool:
        async with self._lock:
            return chunk_id in self._chunks

    async def chunk_count(self) -> int:
        async with self._lock:
            return len(self._chunks)

    async def agent_state(self, agent_id: str) -> Optional[AgentEntity]:
        async with self._lock:
            return self._agents.get(agent_id)

    def _run_chunk_gc(self, *, now: float) -> None:
        candidates: List[str] = []
        for chunk in self._chunks.values():
            if chunk.chunk_id == self._root_chunk_id:
                continue
            if chunk.pinned:
                continue
            if chunk.agents:
                continue
            if chunk.transition_lock_count > 0:
                continue
            if chunk.last_player_left_at is None:
                continue
            if (now - chunk.last_player_left_at) < self.chunk_gc_ttl_seconds:
                continue
            degree = sum(
                1
                for neighbor_id in chunk.neighbors.values()
                if neighbor_id is not None and neighbor_id in self._chunks
            )
            if degree > 1:
                continue
            candidates.append(chunk.chunk_id)

        for chunk_id in candidates:
            chunk = self._chunks.get(chunk_id)
            if chunk is None:
                continue
            for direction, neighbor_id in list(chunk.neighbors.items()):
                if neighbor_id is None:
                    continue
                neighbor = self._chunks.get(neighbor_id)
                if neighbor is not None:
                    neighbor.neighbors[self.OPPOSITE_DIR[direction]] = None
                chunk.neighbors[direction] = None
            self._chunks.pop(chunk_id, None)

    def _attempt_boundary_transition(
        self,
        *,
        cmd: MoveCommand,
        agent: AgentEntity,
        source_chunk: ChunkState,
        direction: str,
        boundary_cell: Cell,
    ) -> Dict[str, Any]:
        source_chunk.transition_lock_count += 1
        target_chunk: Optional[ChunkState] = None
        try:
            boundary_occupant = source_chunk.occupancy.get(boundary_cell)
            if boundary_occupant is not None and boundary_occupant != cmd.agent_id:
                return {
                    "ok": False,
                    "blocked_at": {"x": boundary_cell[0], "y": boundary_cell[1]},
                    "blocker": {"id": boundary_occupant},
                }

            to_chunk_id = self._get_or_create_neighbor(
                source_chunk_id=source_chunk.chunk_id,
                direction=direction,
            )
            target_chunk = self._chunks[to_chunk_id]
            target_chunk.transition_lock_count += 1

            to_x, to_y = self._map_destination(boundary_cell, direction)
            target_occupant = target_chunk.occupancy.get((to_x, to_y))
            if target_occupant is not None and target_occupant != cmd.agent_id:
                return {
                    "ok": False,
                    "blocked_at": {"x": to_x, "y": to_y},
                    "blocker": {"id": target_occupant},
                }

            old_pos = (agent.x, agent.y)
            source_chunk.occupancy.pop(old_pos, None)
            source_chunk.agents.discard(agent.agent_id)
            if not source_chunk.agents:
                source_chunk.last_player_left_at = self._clock()

            target_chunk.occupancy[(to_x, to_y)] = agent.agent_id
            target_chunk.agents.add(agent.agent_id)
            target_chunk.last_player_left_at = None
            agent.chunk_id = target_chunk.chunk_id
            agent.x = to_x
            agent.y = to_y
            cmd.path_index += 1

            return {
                "ok": True,
                "from_chunk_id": source_chunk.chunk_id,
                "to_chunk_id": target_chunk.chunk_id,
                "from": {"x": boundary_cell[0], "y": boundary_cell[1]},
                "to": {"x": to_x, "y": to_y},
            }
        finally:
            source_chunk.transition_lock_count -= 1
            if target_chunk is not None:
                target_chunk.transition_lock_count -= 1

    def _get_or_create_neighbor(self, *, source_chunk_id: str, direction: str) -> str:
        source = self._chunks[source_chunk_id]
        existing = source.neighbors.get(direction)
        if existing is not None and existing in self._chunks:
            return existing

        key = (source_chunk_id, direction)
        self._neighbor_lock_refcnt[key] = self._neighbor_lock_refcnt.get(key, 0) + 1
        try:
            existing = source.neighbors.get(direction)
            if existing is not None and existing in self._chunks:
                return existing

            neighbor_chunk = self._new_chunk()
            self._chunks[neighbor_chunk.chunk_id] = neighbor_chunk
            source.neighbors[direction] = neighbor_chunk.chunk_id
            neighbor_chunk.neighbors[self.OPPOSITE_DIR[direction]] = source_chunk_id
            return neighbor_chunk.chunk_id
        finally:
            refcnt = self._neighbor_lock_refcnt.get(key, 0) - 1
            if refcnt <= 0:
                self._neighbor_lock_refcnt.pop(key, None)
            else:
                self._neighbor_lock_refcnt[key] = refcnt

    def _map_destination(self, boundary_cell: Cell, direction: str) -> Cell:
        src_x, src_y = boundary_cell
        if direction == "W":
            return (self.width - 1, src_y)
        if direction == "E":
            return (0, src_y)
        if direction == "S":
            return (src_x, self.height - 1)
        if direction == "N":
            return (src_x, 0)
        raise TickEngineError("invalid_direction")

    def _boundary_direction(self, *, current: Cell, nxt: Cell) -> Optional[str]:
        cur_x, cur_y = current
        nxt_x, nxt_y = nxt
        dx = nxt_x - cur_x
        dy = nxt_y - cur_y
        if abs(dx) + abs(dy) != 1:
            return None
        if nxt_x == 0 and dx < 0:
            return "W"
        if nxt_x == self.width - 1 and dx > 0:
            return "E"
        if nxt_y == 0 and dy < 0:
            return "S"
        if nxt_y == self.height - 1 and dy > 0:
            return "N"
        return None

    def _emit_chunk_delta(self, chunk: ChunkState, *, events: List[Dict[str, Any]]) -> None:
        payload = {
            "chunk_id": chunk.chunk_id,
            "tick": self._tick,
            "agents": self._agent_snapshots(chunk),
            "events": list(events),
        }
        for agent_id in list(chunk.agents):
            self._emit_to_agent(agent_id, {"type": "chunk_delta", "payload": payload})

    def _resolve_chunk(
        self,
        *,
        chunk_id: Optional[str],
        agent_id: Optional[str],
    ) -> ChunkState:
        if chunk_id is not None:
            chunk = self._chunks.get(chunk_id)
            if chunk is None:
                raise TickEngineError("chunk_not_found")
            return chunk

        if agent_id is not None:
            agent = self._agents.get(agent_id)
            if agent is None:
                raise TickEngineError("agent_not_found")
            chunk = self._chunks.get(agent.chunk_id)
            if chunk is None:
                raise TickEngineError("chunk_not_found")
            return chunk

        return self._chunks[self._root_chunk_id]

    def _new_chunk(self, chunk_id: Optional[str] = None, *, pinned: bool = False) -> ChunkState:
        now = self._clock()
        if chunk_id is None:
            self._chunk_serial += 1
            chunk_id = f"chunk-{self._chunk_serial}"
        else:
            try:
                serial = int(chunk_id.split("-", 1)[1])
                self._chunk_serial = max(self._chunk_serial, serial)
            except (IndexError, ValueError):
                pass
        return ChunkState(
            chunk_id=chunk_id,
            width=self.width,
            height=self.height,
            tiles_static=["." * self.width for _ in range(self.height)],
            neighbors={direction: None for direction in self.DIRECTIONS},
            occupancy={},
            agents=set(),
            created_at=now,
            last_player_left_at=now,
            pinned=pinned,
            seed=0,
        )

    def _build_chunk_static_payload(self, chunk: ChunkState) -> Dict[str, Any]:
        return {
            "chunk_id": chunk.chunk_id,
            "size": {"w": self.width, "h": self.height},
            "tiles": list(chunk.tiles_static),
            "legend": {".": "floor"},
            "neighbors": dict(chunk.neighbors),
            "tick_base": self._tick,
        }
