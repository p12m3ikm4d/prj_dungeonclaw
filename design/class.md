# Class Design

본 문서는 Python/FastAPI 백엔드 구현을 위한 클래스/모듈 설계를 정의한다.

## 1. Domain Class Diagram

```mermaid
classDiagram
    class Agent {
      +str id
      +str name
      +str chunk_id
      +int x
      +int y
      +dict status
      +AgentCommandState command_state
      +str? current_server_cmd_id
    }

    class AgentCommand {
      +str server_cmd_id
      +str client_cmd_id
      +str agent_id
      +CommandType type
      +dict payload
      +CommandStatus status
      +int accepted_tick
      +list~Cell~ path
      +int progress
      +str? fail_reason
    }

    class Chunk {
      +str chunk_id
      +list~str~ tiles_static
      +dict neighbors
      +dict agents
      +dict occupancy
      +int created_at
      +int? last_player_left_at
      +bool pinned
      +int seed
    }

    class WorldDirectory {
      +dict chunks
      +Chunk get(chunk_id)
      +str get_or_create_neighbor(src_chunk_id, dir)
      +void unlink_for_gc(chunk_id)
      +list~str~ gc_candidates(now_ms)
    }

    class TickEngine {
      +int tick
      +int tick_hz
      +void tick_once(now_ms)
      +void start(loop)
      +void stop()
    }

    class CommandCoordinator {
      +Challenge request(agent_id, client_cmd_id, cmd)
      +Ack answer(agent_id, server_cmd_id, sig, proof)
      +Result complete(server_cmd_id)
      +Result fail(server_cmd_id, reason, meta)
    }

    class PathfindingService {
      +list~Cell~ find_path(chunk, from_cell, to_cell)
    }

    class Broadcaster {
      +void publish(chunk_id, event)
      +AsyncIterator subscribe_sse(chunk_id, last_event_id)
      +AsyncIterator subscribe_ws(chunk_id, role)
      +list replay(chunk_id, from_event_id)
    }

    class SnapshotService {
      +dict build_chunk_snapshot(chunk_id)
      +dict build_agent_snapshot(agent_id)
    }

    WorldDirectory "1" --> "*" Chunk
    Chunk "1" --> "*" Agent
    Agent "1" --> "0..1" AgentCommand
    TickEngine --> WorldDirectory
    TickEngine --> PathfindingService
    TickEngine --> CommandCoordinator
    TickEngine --> Broadcaster
    CommandCoordinator --> AgentCommand
    SnapshotService --> WorldDirectory
    SnapshotService --> Broadcaster
```

## 2. Core Enums and Value Objects

### 2.1 Enums

- `CommandType`: `MOVE_TO`, `SAY`
- `CommandStatus`: `PENDING_CHALLENGE`, `QUEUED`, `EXECUTING`, `COMPLETED`, `FAILED`
- `AgentCommandState`: `IDLE`, `EXECUTING`
- `FailReason`: `BLOCKED`, `UNREACHABLE`, `OUT_OF_BOUNDS`, `RATE_LIMITED`, `AUTH_FAILED`, `EXPIRED_CHALLENGE`, `INVALID_CMD`, `BUSY`
- `Direction`: `N`, `E`, `S`, `W`

### 2.2 Value Objects

- `Cell(x:int, y:int)`
- `ChunkTransition(from_chunk_id, to_chunk_id, from_cell, to_cell, tick)`
- `Challenge(nonce, expires_at, difficulty, server_cmd_id)`
- `EventEnvelope(type, trace_id, server_ts_ms, payload)`

## 3. Application Service Interfaces

### 3.1 `CommandCoordinator`

- 입력 검증: 좌표 범위, 에이전트 busy 상태, rate limit
- 챌린지 검증: nonce 만료/서명/난이도 검증
- 출력 보장: ack는 단 한번, result는 완료/실패 중 하나만

### 3.2 `TickEngine`

틱 내 처리 순서:
1. 인증 완료 명령을 큐에서 executing으로 승격
2. executing 명령 next step 시도
3. 이동 성공 또는 blocked 실패 처리
4. 경계 전환 필요 시 원자 전환 수행
5. chunk_delta + command_result 이벤트 발행

### 3.3 `WorldDirectory`

- 이웃 청크 생성은 lock 획득 후 수행
- GC 삭제 시 이웃 링크 역참조 정리 보장
- pinned 또는 degree>1 청크는 GC 제외

### 3.4 `Broadcaster`

- `event_id={chunk_id}:{tick}:{seq}` 채번
- chunk별 ring buffer 유지
- replay 실패 시 `resync_required` 이벤트 생성

## 4. Data Validation Contracts

- `move_to.x/y`: 0..49
- `tiles_static`: 길이 50 문자열 50개
- `neighbors` 키 제한: `N/E/S/W`
- `say.text`: UTF-8 기준 1..200, 단일 라인 정규화

## 5. Error Handling Contract

- recoverable: `rate_limited`, `busy`, `unreachable`, `blocked`
- non-recoverable(현재 명령 기준): `invalid_cmd`, `auth_failed`, `expired_challenge`
- transport-level: WS disconnect -> agent snapshot 기반 재연결

## 6. Testability Hooks

- `TickEngine.tick_once()`는 동기 단위 테스트 가능해야 한다.
- `PathfindingService`는 seed 고정 맵 fixture로 결정론 테스트를 제공한다.
- `WorldDirectory.get_or_create_neighbor()`는 동시성 락 시뮬레이션 테스트를 제공한다.

## Revision

| Date | Author | Summary | Impacted Sections |
|---|---|---|---|
| 2026-02-21 | Codex | 도메인/애플리케이션 클래스, enum, 서비스 인터페이스 정의 | All |
