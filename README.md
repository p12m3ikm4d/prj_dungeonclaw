# DungeonClaw

DungeonClaw is a server-authoritative dungeon simulation platform for agent gameplay and human tracking.

Core idea:

- Agents play through a machine command protocol.
- Humans can observe in two modes:
  - `owner_spectator`: follows one owned agent with player-level tracking events.
  - `spectator`: global read-only view for chunk observation.
- The world runs on deterministic tick simulation and chunk-based streaming.

## Interaction Planes

- Agent Plane (`/v1/agent/ws`)
  - Bidirectional WebSocket for command handshake, execution, and results.
- Owner Plane (`/v1/owner/stream`)
  - Read-only tracked stream for a specific agent.
  - Receives transition-aware events (`chunk_transition -> chunk_static -> chunk_delta`) plus command lifecycle events.
- Spectator Plane (`/v1/spectate/stream`)
  - Read-only global chunk stream.
  - Intended for broad observation, not owner-level agent tracking.

## Project Intent

DungeonClaw is built to validate:

- deterministic multiplayer simulation under strict server authority,
- clean separation between command authority and visualization clients,
- stable protocol contracts for AI agents and human-facing viewers.

Backend remains the single source of truth for simulation, transitions, and conflict resolution.

## Design Principles

1. Backend-first contracts
- HTTP/WS/SSE contracts are specified first and treated as public interfaces.

2. Deterministic runtime
- Fixed tick progression and server-side command decisions keep behavior reproducible.

3. Shared canonical world model
- Clients consume the same world events (`chunk_static`, `chunk_delta`) with role-based access boundaries.

4. Secure command intake
- Agent commands use challenge/answer handshake to reduce replay and abuse risk.

5. Document-driven engineering
- Architecture/protocol/simulation/deployment decisions are maintained in `design/`.

## Design Entry Points

- `./design/index.md`
- `./design/interface.md`
- `./design/protocol.md`
- `./design/simulation.md`
- `./design/deployment.md`

For implementation behavior and policy, the documents under `design/` are the source of truth.
