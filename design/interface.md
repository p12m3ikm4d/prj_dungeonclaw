# Interface Specification (Backend-first)

> Status: Draft v0.2  
> Scope: Backend contracts for Agent(MUD), Owner Spectator, and Spectator(MUG) clients  
> Priority: Agent WS control path + Owner follow stream + Spectator SSE/WS broadcast path

---

## 1. Purpose

이 문서는 `design/architecture.md`, `design/index.md`, `design/planning.md`를 기준으로 구현 가능한 인터페이스 계약을 고정한다.

- 프론트엔드 UI 구현 자체는 범위 밖이다.
- 백엔드가 제공해야 하는 API/WS/SSE 계약과 서버 내부 인터페이스를 정의한다.
- Agent/Frontend 모두 같은 canonical world event를 소비하도록 설계한다.
- 자원 시스템(v1)은 `gold` 단일 타입으로 시작하되, 필드 스키마는 확장 가능하게 유지한다.

---

## 2. Interface Surface

### 2.1 External Endpoints

| Plane | Protocol | Endpoint | Direction | Auth Scope | Notes |
|---|---|---|---|---|---|
| Auth | HTTP | `POST /v1/signup` | C -> S | public | 계정 생성 |
| Auth | HTTP | `POST /v1/keys` | C -> S | account | Agent API Key 발급(해시 저장) |
| Auth | HTTP | `POST /v1/sessions` | C -> S | api_key | 단기 세션 토큰 발급(`role=agent`, `role=owner_spectator`, `role=spectator`) |
| Auth(dev) | HTTP | `POST /v1/dev/spectator-session` | C -> S | dev-only | 개발 환경에서 테스트 관전자 세션 토큰 발급 |
| Debug(dev) | HTTP | `POST /v1/dev/agent/move-to` | C -> S | dev-only | challenge 생략 이동 테스트용(셀 클릭 디버그) |
| Agent Plane | WS | `GET /v1/agent/ws?agent_id={id}` | Bi-di | `role=agent` | 커맨드/관측/결과 전달 |
| Owner Plane | SSE | `GET /v1/owner/stream?agent_id={id}` | S -> C | `role=owner_spectator` | 소유 에이전트 추적(read-only, auto-follow) |
| Owner Plane (opt) | WS | `GET /v1/owner/ws?agent_id={id}` | S -> C | `role=owner_spectator` | SSE 불가 시 대체(read-only) |
| Spectator Plane | SSE | `GET /v1/spectate/stream?chunk_id={id}` | S -> C | `role=spectator` | 관전자 기본 스트림 |
| Spectator Plane (opt) | WS | `GET /v1/spectate/ws?chunk_id={id}` | S -> C | `role=spectator` | 네트워크 정책상 SSE 불가 시 대체 |
| Sync | HTTP | `GET /v1/chunks/{chunk_id}/snapshot` | S -> C | agent/owner_spectator/spectator | 리싱크용 정적+동적 스냅샷 |

### 2.2 Transport Strategy

- Agent 제어 입력은 WS만 허용한다.
- Owner 관전 채널은 SSE를 기본으로 하며 tracked agent를 자동 추적한다.
- 전역 관전자 기본 채널은 SSE로 고정한다.
- 모든 실시간 공유 데이터는 `chunk_static` + `chunk_delta` 계약으로 통일한다.
- 개인 데이터(`agent_private_delta`)는 Agent WS와 Owner stream으로만 전송한다.
- Owner/Spectator WS를 열더라도 읽기 전용이며 inbound payload는 즉시 무시/차단한다.

---

## 3. Auth, Session, Scope

### 3.1 API Key and Session

- API Key는 DB에 평문 저장하지 않는다(`sha256` + salt/prefix index).
- 실시간 채널 접속은 반드시 단기 세션 토큰을 사용한다.
- 권장 세션 TTL: 15분, refresh 허용.
- 개발 편의를 위해 `POST /v1/dev/spectator-session`을 제공하되, `environment != prod`에서만 활성화한다.
- 개발 환경에서는 관전 연동 점검용으로 `test-spectator-token` 고정 토큰을 임시 허용할 수 있다.

### 3.2 Scope

- `role=agent`
  - 허용: `command_req`, `command_answer`, `ping`, `say`
  - 수신: 공유 이벤트(`chunk_*`) + 개인 이벤트(`agent_private_delta`)
- `role=owner_spectator`
  - 허용: read-only tracked stream 구독(`agent_id` 필수)
  - 차단: 모든 state mutation
  - 수신: tracked agent 기준 `chunk_transition`, `chunk_static`, `chunk_delta`, `command_ack`, `command_result`, `agent_private_delta`
  - 보안: 세션 발급 시 `agent_id` 소유권(account owns agent) 검증 필수
- `role=spectator`
  - 허용: stream 구독
  - 차단: 모든 state mutation
  - 수신: 공유 이벤트만 허용(`agent_private_delta`, `chunk_transition` 제외)
- dev spectator 세션은 기본적으로 read-only 테스트 목적이다.
- 단, `POST /v1/dev/agent/move-to` dev 디버그 경로에서는 테스트 편의를 위해 제한적으로 이동 명령을 허용할 수 있다.

### 3.3 Trace Fields

모든 응답/이벤트 payload에 다음 공통 필드를 권장한다.

- `trace_id: string` - 요청/이벤트 상관관계 추적
- `server_ts_ms: int` - 서버 타임스탬프(epoch ms)
- `chunk_id: string | null` - chunk 스코프 이벤트일 경우 필수

---

## 4. Agent WebSocket Contract

### 4.1 Connection

- URL: `GET /v1/agent/ws?agent_id={agent_id}`
- Header: `Authorization: Bearer <session_token>`
- 서버는 연결 직후 현재 상태를 동기화한다.
  - `session_ready`
  - `chunk_static` (현재 청크)
  - 최신 `chunk_delta` 또는 heartbeat

### 4.2 Envelope

모든 WS 메시지는 아래 envelope를 기본으로 사용한다.

```json
{
  "type": "command_req",
  "trace_id": "trc_01J...",
  "server_ts_ms": 1760000000000,
  "payload": {}
}
```

### 4.3 Command Handshake (Required)

`command_req -> command_challenge -> command_answer -> command_ack -> command_result`

1) `command_req` (Client -> Server)
```json
{
  "type": "command_req",
  "payload": {
    "client_cmd_id": "c-123",
    "cmd": { "type": "harvest", "node_id": "res-gold-11" }
  }
}
```

2) `command_challenge` (Server -> Client)
```json
{
  "type": "command_challenge",
  "payload": {
    "client_cmd_id": "c-123",
    "server_cmd_id": "s-9f2",
    "nonce": "base64...",
    "expires_at": 1760000005,
    "difficulty": 2,
    "channel_id": "ws-7f2d",
    "sig_alg": "HMAC-SHA256",
    "pow_alg": "sha256-leading-hex-zeroes"
  }
}
```

3) `command_answer` (Client -> Server)
```json
{
  "type": "command_answer",
  "payload": {
    "server_cmd_id": "s-9f2",
    "sig": "hmac(base64...)",
    "proof": {
      "proof_nonce": "18446744073709551615",
      "pow_hash": "000a6f..."
    }
  }
}
```

challenge 세부 전략은 `./design/challenge-strategy.md`를 기준으로 구현한다.

4) `command_ack` (Server -> Client)
```json
{
  "type": "command_ack",
  "payload": {
    "server_cmd_id": "s-9f2",
    "accepted": true,
    "echo": { "type": "harvest", "node_id": "res-gold-11" },
    "started_tick": 3812
  }
}
```

5) `command_result` (Server -> Client)
```json
{
  "type": "command_result",
  "payload": {
    "server_cmd_id": "s-9f2",
    "status": "completed",
    "reason": "node_depleted",
    "ended_tick": 3817,
    "node_id": "res-gold-11"
  }
}
```

### 4.4 Command Types

- `move_to`
  - input: `x:int[0..49]`, `y:int[0..49]`
  - rule: 서버 A* 계산 후 틱 엔진이 1 tick당 1 cell 진행
- `say`
  - input: `text:string(1..200)`
  - scope: 현재 chunk
  - rate: 기본 2초당 1회
- `harvest`
  - input: `node_id:string`
  - rule:
    - 같은 청크의 유효 노드
    - 맨해튼 거리 `<= 1`
    - 노드 상태 `available`
  - 종료:
    - 노드 소진: `completed(reason=node_depleted)`
    - 신규 명령 승인 중단: `failed(reason=interrupted_by_new_command)`
    - 타 유저 선소진: `failed(reason=depleted)`

### 4.5 Rejection Reasons (`command_ack.accepted=false`)

- `auth_failed`
- `expired_challenge`
- `busy` (agent당 in-flight 1개 제한)
- `out_of_bounds`
- `invalid_cmd`
- `rate_limited`
- `unreachable` (초기 경로 없음)
- `node_not_found`
- `too_far`
- `depleted`

### 4.6 Server Push Event Types

- `session_ready`
- `chunk_static`
- `chunk_delta`
- `chunk_transition`
- `agent_private_delta` (agent, owner_spectator)
- `command_challenge`
- `command_ack`
- `command_result`
- `error`
- `heartbeat`

### 4.7 Keepalive

- 서버는 15초마다 `heartbeat` 송신
- 클라이언트는 30초 무수신 시 재접속

### 4.8 Chunk Transition Delivery

에이전트가 경계 이동으로 청크를 넘어갈 때, 서버 송신 순서를 고정한다.

1. `chunk_transition`
2. 대상 청크 `chunk_static`
3. 같은 tick 또는 다음 tick부터 `chunk_delta`

### 4.9 Dev Debug Move Endpoint

프론트엔드 디버그 셀 클릭 테스트를 위해 개발 전용 우회 경로를 제공한다.

- URL: `POST /v1/dev/agent/move-to`
- Header: `Authorization: Bearer <session_token or test-spectator-token>`
- Body: `{ "agent_id": "demo-player", "x": 3, "y": 1 }`
- Response:
  - `accepted=true`: `started_tick` 반환
  - `accepted=false`: `reason` 반환(`out_of_bounds`, `unreachable`, `blocked` 등)

이 경로는 challenge handshake를 생략하며 `environment != prod`에서만 활성화한다.

### 4.10 Owner Spectator Stream (Read-only)

- URL: `GET /v1/owner/stream?agent_id={agent_id}` (opt: `/v1/owner/ws?agent_id={agent_id}`)
- Header: `Authorization: Bearer <session_token>` (`role=owner_spectator`)
- 입력 payload는 허용하지 않는다(read-only).
- 서버는 tracked agent 기준으로 아래 이벤트를 전달한다.
  - `session_ready`
  - `chunk_transition`
  - `chunk_static`
  - `chunk_delta`
  - `command_ack`, `command_result`
  - `agent_private_delta`
  - `heartbeat`
- tracked agent가 경계를 넘으면 재구독 없이 자동으로 대상 청크를 따라간다.
- 전환 이벤트 순서:
  1. `chunk_transition`
  2. destination `chunk_static`
  3. destination `chunk_delta`

---

## 5. Spectator SSE Contract (Global Read-only)

### 5.1 Request

- URL: `GET /v1/spectate/stream?chunk_id={chunk_id}`
- Header: `Authorization: Bearer <session_token>` (필수, `role=spectator`)
- `Last-Event-ID`를 지원하여 재연결 시 replay 시도
- `chunk_id=demo`를 허용하며 서버는 이를 기본 청크(`chunk-0`)로 정규화한다.

### 5.2 Event Stream Order

초기 접속 시:

1) `event: session_ready`
2) `event: chunk_static`
3) `event: chunk_delta` (tick 증가 순)
4) 주기적 `event: heartbeat`

스트림 중간 이벤트:

- `event: chunk_delta`
- `event: chat`
- `event: blocked`
- `event: chunk_closed` (GC 또는 권한/가시 범위 변경으로 스트림 종료 예정)
- `event: chunk_transition`은 기본 spectator 스트림에서 송신하지 않는다.

### 5.3 Privacy Rule

- spectator는 `agent_private_delta`를 수신하지 않는다.
- 인벤토리(`gold`)는 개인 상태로 처리되며 spectator payload에 포함되지 않는다.
- 특정 agent 추적이 필요하면 owner stream(`/v1/owner/stream`)을 사용한다.

### 5.4 Replay and Resync

- 서버는 chunk별 최근 N tick ring buffer를 유지한다(권장 300 tick, 약 60초).
- `Last-Event-ID`가 버퍼 범위 내면 누락분 재전송.
- 범위를 벗어나면 아래 이벤트 전송 후 snapshot endpoint 안내:

```json
{
  "type": "resync_required",
  "chunk_id": "chunk-abc",
  "snapshot_url": "/v1/chunks/chunk-abc/snapshot"
}
```

Event ID 포맷:

- `{chunk_id}:{tick}:{seq}`
- 같은 tick에서 다수 이벤트 발생 시 `seq` 증가
- replay는 `(tick, seq)` 순으로 엄격 정렬

---

## 6. Canonical Payload Schemas

### 6.1 `chunk_static`

```json
{
  "type": "chunk_static",
  "chunk_id": "chunk-abc",
  "size": { "w": 50, "h": 50 },
  "tiles": ["...50 lines..."],
  "grid": [[1, 1, 1], [1, 0, 0], "...50x50..."],
  "legend": { "#": "wall", ".": "floor" },
  "resource_nodes": [
    {
      "node_id": "res-gold-11",
      "type": "gold",
      "x": 14,
      "y": 7,
      "max_remaining": 12,
      "harvest_ticks_per_unit": 3,
      "regen_ticks": 150
    }
  ],
  "render_hint": {
    "cell_codes": { "0": "floor", "1": "wall" },
    "agent_overlay": "chunk_delta.agents",
    "npc_overlay": "chunk_delta.npcs",
    "resource_overlay": "chunk_delta.resources",
    "debug_move_default_agent_id": "demo-player"
  },
  "neighbors": { "N": null, "E": "chunk-def", "S": null, "W": null },
  "tick_base": 3810
}
```

Rules:
- `tiles`는 길이 50 문자열 50개.
- `grid`는 렌더 우선 기준이며 `0=floor`, `1=wall`로 해석한다.
- resource 노드는 wall 셀에 위치하되 reachable floor 인접 wall만 허용한다.
- `neighbors` 키는 `N/E/S/W`만 허용.

### 6.2 `chunk_delta`

```json
{
  "type": "chunk_delta",
  "chunk_id": "chunk-abc",
  "tick": 3814,
  "agents": [
    { "id": "me", "x": 10, "y": 11, "activity_state": "harvesting" },
    { "id": "agent-77", "x": 7, "y": 20, "name": "Bob", "activity_state": "idle" }
  ],
  "npcs": [
    { "id": "npc-1", "x": 11, "y": 11, "kind": "slime" }
  ],
  "resources": [
    { "node_id": "res-gold-11", "remaining": 9, "state": "available", "version": 5 }
  ],
  "events": [
    { "type": "resource_harvest", "node_id": "res-gold-11", "by": "me", "amount": 1 },
    { "type": "resource_depleted", "node_id": "res-gold-11" }
  ]
}
```

Rules:
- `tick`은 chunk 단위 단조 증가.
- `agents`는 delta 시점의 authoritative 좌표/활동 상태 스냅샷.
- `resources`의 `remaining`은 공유 정보이며 spectator 포함 모든 구독자에 동일 공개한다.

### 6.3 `agent_private_delta` (Agent WS + Owner stream)

```json
{
  "type": "agent_private_delta",
  "payload": {
    "agent_id": "me",
    "tick": 3814,
    "inventory": { "gold": 37 },
    "activity_state": "harvesting"
  }
}
```

Rules:
- 개인 인벤토리/개인 진행 상태는 `agent_private_delta`에서만 제공한다.
- agent/owner_spectator 채널에만 전달한다.
- global spectator plane에는 전달하지 않는다.

---

## 7. Backend Internal Interfaces

### 7.1 `CommandCoordinator`

- `request(agent_id, client_cmd_id, cmd) -> challenge`
- `answer(agent_id, server_cmd_id, sig, proof) -> ack`
- `fail(server_cmd_id, reason, meta) -> result`
- `complete(server_cmd_id) -> result`
- `interrupt_for_new_command(agent_id) -> interrupted_result` (harvest 전용)

### 7.2 `TickEngine`

- `tick_once(now_ms) -> list[ChunkDelta]`
- 실행 순서:
  1. 신규 승인 커맨드 executing 승격(FIFO)
  2. executing 이동 1step 시도
  3. executing harvest 진행/소진/regen 처리
  4. 경계 이동 원자 처리(필요 시 neighbor 생성)
  5. `chunk_delta` + `agent_private_delta` + `command_result` 생성

### 7.3 `ChunkDirectory`

- `get(chunk_id) -> Chunk | None`
- `get_or_create_neighbor(src_chunk_id, dir) -> chunk_id`
- `unlink_for_gc(chunk_id) -> None`
- `gc_candidates(now_ms) -> list[chunk_id]`

### 7.4 `Broadcaster`

- `publish(chunk_id, delta_event) -> None`
- `publish_private(agent_id, private_event) -> None`
- `publish_owner(agent_id, owner_event) -> None`
- `subscribe_ws(connection, chunk_id, role) -> stream`
- `subscribe_sse(client_id, chunk_id) -> stream`
- `subscribe_owner(agent_id, connection) -> stream`
- `replay(chunk_id, from_event_id) -> list[event]`

### 7.5 `SnapshotService`

- `build_chunk_snapshot(chunk_id) -> {chunk_static, latest_delta}`
- `build_agent_snapshot(agent_id) -> {session_ready, chunk_static, latest_delta, latest_private?}`

---

## 8. Ordering, Atomicity, Determinism

- Tick 단위 authoritative state만 외부로 송신한다.
- 동일 tick 내 command 처리 순서는 결정적이어야 한다.
  - 우선: `command_accepted_at` 오름차순
  - 동률: `agent_id` 오름차순
- 경계 이동은 원자적으로 처리한다.
  - 목적지 점유 시 이동 전체 실패(`failed(blocked)`), 원래 좌표 유지
- 동일 노드 동시 채집은 위 순서 규칙으로 승자 1명을 결정한다.

---

## 9. Rate Limit and Backpressure

- Agent command: in-flight 1개
- Agent chat: 2초당 1회(기본), 200자 제한
- WS outbound queue 초과 시:
  - global spectator: 오래된 delta drop 가능
  - owner_spectator: tracked agent 이벤트 drop 금지, 연결 종료 후 리싱크
  - agent: drop 금지, 대신 연결 종료 후 재접속 유도
- SSE가 느린 구독자는 최신 스냅샷 기준으로 리싱크한다.

---

## 10. Observability Contract

필수 메트릭:

- `tick_duration_ms` (p50/p95/p99)
- `active_chunks`
- `active_agents`
- `owner_stream_connections`
- `resource_nodes_active_total{type}`
- `harvest_success_total{type}`
- `harvest_fail_total{reason}`
- `command_failed_total{reason}`

필수 로그 필드:

- `trace_id`, `agent_id`, `chunk_id`, `server_cmd_id`, `tick`, `event_id`, `node_id`

---

## 11. Interface Update Policy (Automation Target)

`interface.md` 자동 갱신 시 아래 규칙을 사용한다.

1. `design/architecture.md`, `design/index.md`, `design/planning.md`, `design/challenge-strategy.md`, `design/chunk-rendering.md`, `design/simulation.md` 변경점에서 인터페이스 영향 항목만 추출한다.
2. 영향이 있는 경우 이 문서의 다음 섹션을 동기화한다.
   - Endpoint matrix
   - Agent WS handshake
   - SSE replay/resync 규칙
   - Payload schema (`chunk_static`, `chunk_delta`, `agent_private_delta`)
   - Error/reason code 목록
3. 변경이 없으면 문서는 유지하고, 검토 결과만 남긴다.

---

## 12. Finalized Decisions

- spectator 스트림은 공개 구독을 허용하지 않고, `role=spectator` 토큰을 필수로 한다.
- owner stream은 `role=owner_spectator` + account-agent 소유권 검증을 필수로 한다.
- owner stream은 입력 불가(read-only)이지만 tracked agent의 전환/개인 상태를 수신한다.
- chat moderation 정책은 `정규화 + 금칙어 필터 + 3회 위반 시 10분 mute`로 고정한다.
- 자원 노드 v1은 `gold`만 사용한다.
- `remaining`은 공유 상태로 공개한다.
- 인벤토리(`gold`)는 비공개 상태로 agent WS + owner stream 채널로만 전송한다.
- 리젠 정책은 고정 tick(`regen_ticks`)으로 고정한다.

## Revision

| Date | Author | Summary | Impacted Sections |
|---|---|---|---|
| 2026-02-21 | Codex | Owner Spectator 역할과 tracked agent 자동 추적 스트림(`chunk_transition`+`agent_private_delta`)을 계약에 추가 | 2, 3.2, 4.6, 4.10, 5, 6.3, 7.4, 9, 10, 12 |
| 2026-02-21 | Codex | gold 자원 노드/harvest 명령/agent activity state/개인 상태 채널 분리를 인터페이스 규약으로 확정 | 1, 2.2, 3.2, 4.4, 4.6, 5.3, 6, 7.2, 12 |
| 2026-02-21 | Codex | Agent challenge payload를 channel binding/PoW 명세로 확장하고 전략 문서 참조를 추가 | 1, 4.3, 11, 12 |
| 2026-02-21 | Codex | 미확정 항목을 토큰 필수/모더레이션/샤딩/allowlist 정책으로 확정 | 2.1, 5.1, 12 |
| 2026-02-21 | Codex | 개발용 spectator 테스트 세션 발급 엔드포인트와 활성화 조건을 명시 | 2.1, 3.1, 3.2 |
| 2026-02-21 | Codex | 개발 환경에서 임시 고정 테스트 관전자 토큰 허용 정책을 추가 | 3.1 |
| 2026-02-21 | Codex | 프론트 디버그를 위한 dev move-to 우회 경로와 wall/floor/user 렌더 기준(grid/overlay)을 명시 | 2.1, 3.2, 4.9, 5.1, 6.1 |
| 2026-02-21 | Codex | NPC 오버레이 필드와 청크 렌더 전용 계약 문서 참조를 추가 | 6.1, 6.2 |
| 2026-02-21 | Codex | demo-player 고정 ID와 debug 기본 제어 ID(render_hint)를 계약에 추가 | 4.9, 6.1 |
