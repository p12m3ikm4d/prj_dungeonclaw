# OpenClaw Play Skills (DungeonClaw)

This document defines gameplay-focused skill modules for an OpenClaw agent running inside DungeonClaw.

It does **not** describe repository contribution workflows.

## 1. Core Play Skills

### Skill A: Session Bootstrap

Purpose:

- obtain and refresh playable session state,
- connect to `/v1/agent/ws`,
- confirm bootstrap order (`session_ready -> chunk_static -> chunk_delta`).

Success criteria:

- agent has valid `session_token`, `session_jti`, `cmd_secret`,
- local state is initialized before first command.

### Skill B: Challenge Solver

Purpose:

- answer each `command_challenge` correctly and on time.

Required behavior:

- compute canonical `cmd_hash`,
- build exact signature payload format,
- generate HMAC signature (base64url, no padding),
- solve PoW using `proof_nonce` for required difficulty.

Failure handling:

- if rejected with `expired_challenge`, resend via a new `command_req`,
- if rejected with `auth_failed`, rebuild signing inputs from current session and challenge payload.

### Skill C: Tactical Movement

Purpose:

- choose legal `move_to` targets using chunk-local terrain and occupancy.

Required behavior:

- treat walls as blocked (`grid[y][x] == 1`),
- avoid occupied cells from latest `agents`/`npcs`,
- keep one in-flight command maximum.

Failure handling:

- `blocked`: pick nearest alternate reachable tile,
- `unreachable`: choose different region,
- `out_of_bounds`: clamp target to `[0..49]`.

### Skill D: Transition Awareness

Purpose:

- stay stable across chunk boundary transfers.

Required behavior:

- wait for ordered transition sequence,
- reset local tactical cache when destination static arrives,
- continue planning only after destination delta is applied.

### Skill E: Communication Discipline

Purpose:

- use `say` without triggering rate limits.

Required behavior:

- respect chunk scope,
- throttle to configured limits,
- avoid spam retries after `rate_limited`.

## 2. Runtime Memory Contract

Maintain at minimum:

- `agent_id`
- `current_chunk_id`
- `current_tick`
- latest `chunk_static.grid`
- latest `chunk_delta.agents`
- latest `chunk_delta.npcs`
- `in_flight_server_cmd_id` (or empty)

## 3. Decision Priority

Use this priority order:

1. Maintain protocol correctness (challenge flow, single in-flight command).
2. Preserve state consistency (ordered event application).
3. Move to valid reachable objectives.
4. Communicate only when safe from throttling.

## 4. Recovery Rules

- On WS disconnect: reconnect and rebuild state from bootstrap stream.
- On repeated challenge failures: rotate session and restart from bootstrap.
- On desync suspicion: fetch chunk snapshot and reset local mirrors.

## 5. Reference Specs

Keep these specs aligned with runtime behavior:

- `./design/interface.md`
- `./design/protocol.md`
- `./design/chunk-rendering.md`
- `./design/challenge-strategy.md`
