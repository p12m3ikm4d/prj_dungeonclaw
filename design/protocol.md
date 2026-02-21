# Protocol Design

본 문서는 외부 인터페이스 계약(HTTP/WS/SSE)과 메시지 스키마를 정의한다.

## 1. Constants

- `CHUNK_W=50`, `CHUNK_H=50`
- `TICK_HZ=5`
- `MOVE_CELLS_PER_TICK=1`
- `HARVEST_RANGE=1` (Manhattan)
- `RESOURCE_TYPES_V1=["gold"]`
- command in-flight limit: 1 per agent
- chat rate limit: 기본 2초당 1회, 길이 200자

## 2. Endpoint Matrix

| Protocol | Endpoint | Purpose | Auth |
|---|---|---|---|
| HTTP | `POST /v1/signup` | 계정 생성 | public |
| HTTP | `POST /v1/keys` | API Key 발급 | account |
| HTTP | `POST /v1/sessions` | 단기 세션 발급 (`agent`, `owner_spectator`, `spectator`) | api_key/account |
| HTTP(dev) | `POST /v1/dev/spectator-session` | 개발용 관전자 세션 발급 | dev-only |
| HTTP(dev) | `POST /v1/dev/agent/move-to` | challenge 생략 이동 디버그 | dev-only |
| WS | `GET /v1/agent/ws?agent_id={id}` | Agent 양방향 채널 | `role=agent` |
| SSE | `GET /v1/owner/stream?agent_id={id}` | Owner 관전(자동 추적) | `role=owner_spectator` |
| WS(optional) | `GET /v1/owner/ws?agent_id={id}` | Owner 관전 대체 채널(read-only) | `role=owner_spectator` |
| SSE | `GET /v1/spectate/stream?chunk_id={id}` | Spectator 단방향 스트림 | `role=spectator` |
| WS(optional) | `GET /v1/spectate/ws?chunk_id={id}` | Spectator 대체 채널(read-only) | `role=spectator` |
| HTTP | `GET /v1/chunks/{chunk_id}/snapshot` | 리싱크 스냅샷 | agent/owner_spectator/spectator |

## 3. Envelope

WS/SSE JSON payload 공통 envelope:

```json
{
  "type": "chunk_delta",
  "trace_id": "trc_01J...",
  "server_ts_ms": 1760000000000,
  "payload": {}
}
```

## 4. Agent WS Handshake

흐름: `command_req -> command_challenge -> command_answer -> command_ack -> command_result`

### 4.1 `command_req`

```json
{
  "type": "command_req",
  "payload": {
    "client_cmd_id": "c-123",
    "cmd": { "type": "harvest", "node_id": "res-gold-11" }
  }
}
```

### 4.2 `command_challenge`

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

### 4.3 `command_answer`

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

`proof`의 구버전 문자열 포맷은 `proof_nonce`로 간주해 호환 처리할 수 있다.

### 4.4 `command_ack`

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

### 4.5 `command_result`

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

## 5. Command Types

### 5.1 `move_to`

- 입력: `x:int[0..49], y:int[0..49]`
- 의미: 현재 청크 로컬 좌표 이동 의도
- 처리: 서버 A* + 틱 이동

### 5.2 `say`

- 입력: `text:string(1..200)`
- 스코프: chunk
- 규칙: 제어문자 제거, 멀티라인 금지

### 5.3 `harvest`

- 입력: `{ "type": "harvest", "node_id": string }`
- 대상: `chunk_static.resource_nodes[].node_id`
- 시작 조건:
  - 노드 존재
  - 노드 상태 `available`
  - 유저-노드 거리 맨해튼 `<= 1`
- 진행 규칙:
  - `harvest_ticks_per_unit`마다 `remaining -= 1`
  - 개인 인벤토리 `inventory.gold += 1`
- 종료 규칙:
  - 노드 소진: `completed(reason=node_depleted)`
  - 신규 명령 승인으로 중단: `failed(reason=interrupted_by_new_command)`
  - 타 유저가 먼저 소진: `failed(reason=depleted)`

### 5.4 `dev_move_to` (Debug only)

- endpoint: `POST /v1/dev/agent/move-to`
- 입력: `{agent_id:string, x:int, y:int}`
- 인증: `Bearer <session_token or test-spectator-token>`
- dev demo 기본 제어 대상 id는 `demo-player`를 사용한다.
- 의미: challenge handshake 없이 서버 tick 엔진에 이동 명령을 직접 enqueue
- 제한: `environment != prod`, 디버그 메뉴에서만 사용

## 6. Rejection Reasons

`command_ack.accepted=false`인 경우:

- `auth_failed`
- `expired_challenge`
- `busy`
- `out_of_bounds`
- `invalid_cmd`
- `rate_limited`
- `unreachable`
- `node_not_found`
- `too_far`
- `depleted`

## 7. Observation Payloads

### 7.1 `chunk_static`

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

### 7.2 `chunk_delta`

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

### 7.3 `agent_private_delta` (Agent WS + Owner stream)

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
- `chunk_delta`는 공유 채널 데이터이며 spectator도 동일하게 수신한다.
- `agent_private_delta`는 해당 agent WS 및 owner stream에만 전달한다.
- `npcs` 필드는 항상 배열을 사용하며, MVP 단계에서는 빈 배열(`[]`)일 수 있다.

렌더 상세 규칙은 `./design/chunk-rendering.md`를 기준으로 한다.

## 8. Chunk Transition Events

경계 전환 시 Agent 채널 송신 순서:

1. `chunk_transition`
2. destination `chunk_static`
3. `chunk_delta`

```json
{
  "type": "chunk_transition",
  "payload": {
    "agent_id": "me",
    "from_chunk_id": "chunk-abc",
    "to_chunk_id": "chunk-def",
    "from": { "x": 49, "y": 18 },
    "to": { "x": 0, "y": 18 },
    "tick": 3815
  }
}
```

### 8.1 Owner Stream Follow Contract

- owner stream은 tracked `agent_id` 기준으로 자동 추적한다.
- tracked agent가 청크를 넘어가면 재구독 없이 서버가 아래 순서로 전송한다.
  1. `chunk_transition`
  2. destination `chunk_static`
  3. destination `chunk_delta`
- owner stream은 read-only이며 inbound payload를 허용하지 않는다.
- owner stream은 아래 이벤트를 수신한다.
  - `session_ready`
  - `chunk_transition`
  - `chunk_static`
  - `chunk_delta`
  - `command_ack`, `command_result`
  - `agent_private_delta`
  - `heartbeat`

## 9. Spectator SSE Contract (Global Read-only)

- 초기: `session_ready -> chunk_static -> chunk_delta`
- `chunk_id=demo` 요청은 서버에서 `chunk-0`으로 정규화한다.
- keepalive: 15~30초
- event id: `{chunk_id}:{tick}:{seq}`
- `Last-Event-ID` replay 지원
- replay 실패 시 `resync_required` + snapshot 안내
- `chunk_transition`은 기본 spectator 스트림에서 수신하지 않는다.
- spectator는 `agent_private_delta`를 수신하지 않는다.

```json
{
  "type": "resync_required",
  "chunk_id": "chunk-abc",
  "snapshot_url": "/v1/chunks/chunk-abc/snapshot"
}
```

## 10. Ordering and Determinism

- tick authoritative 송신만 허용
- 같은 tick 내 처리 순서:
  - 1순위 `command_accepted_at` 오름차순
  - 2순위 `agent_id` 오름차순

## 11. Security and Abuse Controls

- Spectator stream은 `role=spectator` 토큰이 필수이며 public 구독은 허용하지 않는다.
- Spectator는 state mutation 불가
- Owner stream은 `role=owner_spectator` 토큰 + account-agent 소유권 검증이 필수다.
- Owner stream은 read-only이며 tracked agent 이벤트 관측만 허용한다.
- `POST /v1/dev/spectator-session`은 `environment != prod`에서만 활성화한다.
- `POST /v1/dev/agent/move-to`는 challenge를 생략하는 dev debug 경로이며 `environment != prod`에서만 활성화한다.
- 개발 환경 한정으로 `test-spectator-token`을 관전 연동 검증용 임시 토큰으로 허용할 수 있다.
- chat normalization + rate limit 필수
- chat 위반 정책은 `금칙어 필터 + 3회 위반 시 10분 mute`를 적용한다.
- 챌린지 nonce/만료 검증 필수
- challenge allowlist 예외는 허용하지 않는다.

## 12. Compatibility Policy

- 필드 추가: backward compatible
- 필드 제거/의미 변경: minor 이상 버전 업
- reason code 추가 시 문서와 SDK를 동시 갱신

## 13. Challenge Strategy Link

- 챌린지 세부 구현 전략(anti-replay, 서명 canonical form, PoW 난이도 조정)은 `./design/challenge-strategy.md`를 기준으로 한다.

## Revision

| Date | Author | Summary | Impacted Sections |
|---|---|---|---|
| 2026-02-21 | Codex | Owner Spectator 자동 추적 스트림과 전환/개인상태 수신 규약을 추가 | 2, 7.3, 8.1, 9, 11 |
| 2026-02-21 | Codex | gold 자원 노드/harvest 명령/agent_private_delta 채널 및 공개 remaining 정책을 프로토콜에 추가 | 1, 4, 5, 6, 7, 9 |
| 2026-02-21 | Codex | WS/SSE/HTTP 계약 및 메시지 스키마를 상세 명세로 분리 | All |
| 2026-02-21 | Codex | challenge payload 확장 필드와 전략 문서 연계를 추가 | 4.2, 4.3, 13 |
| 2026-02-21 | Codex | spectator 토큰 필수/채팅 위반 정책/allowlist 비허용 정책을 고정 | 11 |
| 2026-02-21 | Codex | 개발용 spectator 세션 발급 엔드포인트와 prod 비활성 정책을 추가 | 2, 11 |
| 2026-02-21 | Codex | 개발 환경 임시 테스트 토큰(`test-spectator-token`) 허용 정책을 추가 | 11 |
| 2026-02-21 | Codex | 디버그 move-to 경로와 wall/floor/user 렌더 기준(grid + agents overlay), demo chunk 정규화를 추가 | 2, 5.4, 7.1, 9, 11 |
| 2026-02-21 | Codex | NPC 오버레이(`chunk_delta.npcs`)와 렌더 전용 계약 문서 참조를 추가 | 7.1, 7.2 |
| 2026-02-21 | Codex | demo-player 고정 ID와 debug 기본 제어 ID(render_hint)를 프로토콜에 추가 | 5.4, 7.1 |
