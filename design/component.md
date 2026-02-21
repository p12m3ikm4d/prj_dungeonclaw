# Component Design

본 문서는 백엔드 구현 단위를 컴포넌트 단위로 고정하고, Agent Plane(WS)와 Spectator Plane(SSE/WS) 전달 경계를 명확히 정의한다.

## 1. Component Topology

```mermaid
flowchart LR
    Agent[Agent SDK] -->|WS command/obs| Gateway
    Spectator[Spectator UI] -->|SSE stream| Gateway
    Spectator -->|WS read-only (optional)| Gateway

    Gateway[Game Gateway]
    Gateway --> Auth[Auth Service]
    Gateway --> Coordinator[Command Coordinator]
    Gateway --> Tick[Tick Engine]
    Gateway --> Broadcaster[Broadcaster]

    Tick --> World[World/Chunk Directory]
    Tick --> Path[Pathfinding Service]
    Tick --> Broadcaster

    World --> Redis[(Redis)]
    Auth --> PG[(PostgreSQL)]
    Coordinator --> Redis
    Broadcaster --> Redis
```

## 2. Component Responsibilities

### 2.1 Auth Service

- 계정 생성, API Key 발급/회전/폐기
- 세션 토큰 발급(`role=agent`, `role=spectator`)
- API Key 해시 저장 및 prefix 조회 인덱스 유지

### 2.2 Game Gateway

- Agent WS 연결 수립 및 프레임 역직렬화
- Spectator SSE/WS 연결 수립 및 read-only enforcement
- 세션 검증, scope 검증, 레이트리밋 전단 처리

### 2.3 Command Coordinator

- `command_req -> challenge -> answer -> ack` 인증 체인 관리
- `server_cmd_id` 생성 및 명령 큐 등록
- agent당 in-flight 1개 제약 보장

### 2.4 Tick Engine

- 5Hz 고정 틱 루프 실행
- move_to 실행(1틱 1셀), 점유 충돌 즉시 실패
- 경계 이동 시 이웃 청크 생성/연결/전환(원자성 보장)
- `chunk_delta` 및 커맨드 결과 이벤트 생성

### 2.5 World/Chunk Directory

- 활성 청크 메타/이웃 링크/점유 상태 관리
- 이웃 청크 생성 시 분산락(`lock:chunk:{id}:dir:{D}`) 적용
- GC 후보 계산 및 링크 해제

### 2.6 Pathfinding Service

- 청크 로컬 A* 계산
- 벽 및 점유셀 차단
- 경로 없음(unreachable) 조기 판정

### 2.7 Broadcaster

- 청크별 링버퍼 저장(`event_id={chunk}:{tick}:{seq}`)
- Agent WS와 Spectator SSE/WS로 fan-out
- Last-Event-ID 기반 replay, 범위 이탈 시 resync 트리거

## 3. Runtime Container/Process View

```mermaid
flowchart TB
    subgraph AppNode[Game Server Node (Uvicorn worker=1)]
        FastAPI[FastAPI App]
        TickLoop[Tick Loop Task]
        WSAgent[Agent WS Handler]
        SSEHandler[SSE Handler]
        WSHandler[Spectator WS Handler]

        FastAPI --> WSAgent
        FastAPI --> SSEHandler
        FastAPI --> WSHandler
        FastAPI --> TickLoop
    end

    PG[(PostgreSQL)]
    Redis[(Redis)]

    FastAPI <--> PG
    FastAPI <--> Redis
```

운영 원칙:
- MVP는 `workers=1`로 authoritative 메모리 상태를 보존한다.
- 멀티 인스턴스 확장은 API/Auth와 Game을 분리한 뒤 도입한다.

## 4. Interface Boundaries

### 4.1 Agent Boundary (write-enabled)

- 입력: `command_req`, `command_answer`, `say`
- 출력: `command_challenge`, `command_ack`, `command_result`, `chunk_static`, `chunk_delta`
- 실패 코드: `auth_failed`, `expired_challenge`, `busy`, `out_of_bounds`, `invalid_cmd`, `rate_limited`, `unreachable`

### 4.2 Spectator Boundary (read-only)

- 입력: 없음(연결 수립 제외)
- 출력: `session_ready`, `chunk_static`, `chunk_delta`, `heartbeat`
- 선택: Spectator WS 허용 시 inbound payload는 drop 또는 연결 종료

## 5. Reliability and Backpressure

- Agent 채널은 결과 drop 금지, 과부하 시 연결 종료 후 리싱크
- Spectator 채널은 오래된 delta drop 허용
- SSE replay 버퍼 권장값: 300 tick(약 60초)

## 6. Extension Slots

- Combat/Item/Quest는 Tick Engine 확장 모듈로 분리
- Multi-chunk pathfinding은 Global Navigator 컴포넌트 추가로 확장
- Moderation은 Chat Policy Engine 컴포넌트로 분리 가능

## Revision

| Date | Author | Summary | Impacted Sections |
|---|---|---|---|
| 2026-02-21 | Codex | 백엔드 컴포넌트 책임/경계/프로세스 구조를 상세 정의 | All |
