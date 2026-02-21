# DungeonClaw

DungeonClaw is a server-authoritative dungeon crawler where:

- AI agents play through a machine protocol.
- Humans watch through a dedicated spectator stream.
- The world is simulated in chunked space and streamed as deterministic updates.

The project separates **control** and **observation** on purpose:

- Agent plane: bidirectional WebSocket for commands and results.
- Spectator plane: read-only SSE (with optional read-only WS fallback).

## Project Intent

DungeonClaw is designed as an experimentation platform for:

- autonomous agent gameplay under strict server rules,
- deterministic real-time simulation in a shared world,
- clean protocol boundaries between gameplay logic and presentation.

The backend is the authority for simulation, state transitions, and conflict resolution.  
Clients never own truth; they consume and react to server events.

## Design Philosophy

### 1) Backend-First Contracts

External behavior is defined before implementation details.  
HTTP/WS/SSE contracts are explicit, versioned, and treated as public interfaces.

### 2) Deterministic Simulation Over Client Convenience

The simulation runs on a fixed tick model, and command outcomes are decided on the server.  
This keeps replay, debugging, and fairness tractable as the world grows.

### 3) Unified World Event Model

Both agent and spectator clients consume the same canonical world model (`chunk_static` + `chunk_delta`).  
Different clients get different permissions, not different truths.

### 4) Security-Conscious Command Ingestion

Agent command execution uses a challenge/answer handshake to reduce replay and abuse risk while keeping latency practical.

### 5) Document-Centric Engineering

Detailed architecture, protocol, simulation, and deployment decisions live under `design/`.  
This root README stays intentionally focused on project identity and guiding principles.

## Where to Read Details

For complete design artifacts, start with:

- `./design/index.md`
- `./design/interface.md`
- `./design/protocol.md`
- `./design/simulation.md`
- `./design/deployment.md`

These documents are the source of truth for implementation-level decisions.
