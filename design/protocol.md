# Protocol Design

본 문서는 외부 인터페이스 계약(HTTP/WS/SSE)과 메시지 스키마를 정의한다.

## 1. Constants

- `CHUNK_W=50`, `CHUNK_H=50`
- `TICK_HZ=5`
- `MOVE_CELLS_PER_TICK=1`
- command in-flight limit: 1 per agent
- chat rate limit: 기본 2초당 1회, 길이 200자

## 2. Endpoint Matrix

| Protocol | Endpoint | Purpose | Auth |
|---|---|---|---|
| HTTP | `POST /v1/signup` | 계정 생성 | public |
| HTTP | `POST /v1/keys` | API Key 발급 | account |
| HTTP | `POST /v1/sessions` | 단기 세션 발급 | api_key/account |
| HTTP(dev) | `POST /v1/dev/spectator-session` | 개발용 관전자 세션 발급 | dev-only |
| WS | `GET /v1/agent/ws?agent_id={id}` | Agent 양방향 채널 | `role=agent` |
| SSE | `GET /v1/spectate/stream?chunk_id={id}` | Spectator 단방향 스트림 | `role=spectator` |
| WS(optional) | `GET /v1/spectate/ws?chunk_id={id}` | Spectator 대체 채널(read-only) | `role=spectator` |
| HTTP | `GET /v1/chunks/{chunk_id}/snapshot` | 리싱크 스냅샷 | agent/spectator |

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
    "cmd": { "type": "move_to", "x": 12, "y": 41 }
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
    "echo": { "type": "move_to", "x": 12, "y": 41 },
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
    "status": "failed",
    "reason": "blocked",
    "blocked_at": { "x": 7, "y": 20 },
    "blocker": { "id": "agent-77", "name": "Bob", "x": 7, "y": 20 },
    "ended_tick": 3817
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

## 6. Rejection Reasons

`command_ack.accepted=false`인 경우:

- `auth_failed`
- `expired_challenge`
- `busy`
- `out_of_bounds`
- `invalid_cmd`
- `rate_limited`
- `unreachable`

## 7. Observation Payloads

### 7.1 `chunk_static`

```json
{
  "type": "chunk_static",
  "chunk_id": "chunk-abc",
  "size": { "w": 50, "h": 50 },
  "tiles": ["...50 lines..."],
  "legend": { "#": "wall", ".": "floor", "+": "door", "~": "water" },
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
    { "id": "me", "x": 10, "y": 11 },
    { "id": "agent-77", "x": 7, "y": 20, "name": "Bob" }
  ],
  "patches": [
    { "x": 10, "y": 10, "ch": "." },
    { "x": 10, "y": 11, "ch": "@" }
  ],
  "events": [
    { "type": "chat", "scope": "chunk", "from": "agent-77", "text": "비켜!!" },
    { "type": "blocked", "by": "agent-77", "at": { "x": 7, "y": 20 } }
  ],
  "my_command": {
    "server_cmd_id": "s-9f2",
    "state": "executing",
    "progress": 12,
    "target": { "x": 12, "y": 41 }
  }
}
```

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

## 9. Spectator SSE Contract

- 초기: `session_ready -> chunk_static -> chunk_delta`
- keepalive: 15~30초
- event id: `{chunk_id}:{tick}:{seq}`
- `Last-Event-ID` replay 지원
- replay 실패 시 `resync_required` + snapshot 안내

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
- `POST /v1/dev/spectator-session`은 `environment != prod`에서만 활성화한다.
- chat normalization + rate limit 필수
- chat 위반 정책은 `금칙어 필터 + 3회 위반 시 10분 mute`를 적용한다.
- 챌린지 nonce/만료 검증 필수
- challenge allowlist 예외는 허용하지 않는다.

## 12. Compatibility Policy

- 필드 추가: backward compatible
- 필드 제거/의미 변경: minor 이상 버전 업
- reason code 추가 시 문서와 SDK를 동시 갱신

## 13. Challenge Strategy Link

- 챌린지 세부 구현 전략(anti-replay, 서명 canonical form, PoW 난이도 조정)은 `/Users/songchihyun/repos/prj_dungeonclaw/design/challenge-strategy.md`를 기준으로 한다.

## Revision

| Date | Author | Summary | Impacted Sections |
|---|---|---|---|
| 2026-02-21 | Codex | WS/SSE/HTTP 계약 및 메시지 스키마를 상세 명세로 분리 | All |
| 2026-02-21 | Codex | challenge payload 확장 필드와 전략 문서 연계를 추가 | 4.2, 4.3, 13 |
| 2026-02-21 | Codex | spectator 토큰 필수/채팅 위반 정책/allowlist 비허용 정책을 고정 | 11 |
| 2026-02-21 | Codex | 개발용 spectator 세션 발급 엔드포인트와 prod 비활성 정책을 추가 | 2, 11 |
