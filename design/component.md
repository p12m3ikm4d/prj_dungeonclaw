# Component Design

본 문서는 백엔드 구현 단위를 컴포넌트 단위로 고정하고, Agent Plane(WS), Owner Plane, Spectator Plane(SSE/WS) 전달 경계를 명확히 정의한다.

## 1. Component Topology

```mermaid
flowchart LR
    Agent[Agent SDK] -->|WS command/obs| Gateway
    Owner[Owner UI] -->|SSE owner stream| Gateway
    Spectator[Spectator UI] -->|SSE stream| Gateway
    Spectator -->|WS read-only (optional)| Gateway

    Gateway[Game Gateway]
    Gateway --> Auth[Auth Service]
    Gateway --> Coordinator[Command Coordinator]
    Gateway --> Tick[Tick Engine]
    Gateway --> Broadcaster[Broadcaster]

    Tick --> World[World/Chunk Directory]
    Tick --> Path[Pathfinding Service]
    Tick --> Resource[Resource Node Service]
    Tick --> Broadcaster

    World --> Redis[(Redis)]
    Auth --> PG[(PostgreSQL)]
    Coordinator --> Redis
    Broadcaster --> Redis
```

## 2. Component Responsibilities

### 2.1 Auth Service

- 계정 생성, API Key 발급/회전/폐기
- 세션 토큰 발급(`role=agent`, `role=owner_spectator`, `role=spectator`)
- API Key 해시 저장 및 prefix 조회 인덱스 유지

### 2.2 Game Gateway

- Agent WS 연결 수립 및 프레임 역직렬화
- Owner stream 연결 수립(`agent_id` 바인딩, ownership 검증, read-only)
- Spectator SSE/WS 연결 수립 및 read-only enforcement
- 세션 검증, scope 검증, 레이트리밋 전단 처리

### 2.3 Command Coordinator

- `command_req -> challenge -> answer -> ack` 인증 체인 관리
- `server_cmd_id` 생성 및 명령 큐 등록
- agent당 in-flight 1개 제약 보장
- `harvest` 중 신규 명령 승인 시 `interrupted_by_new_command` 정리

### 2.4 Tick Engine

- 5Hz 고정 틱 루프 실행
- `move_to` 실행(1틱 1셀), 점유 충돌 즉시 실패
- `harvest(node_id)` 실행 및 소진/regen 처리
- 경계 이동 시 이웃 청크 생성/연결/전환(원자성 보장)
- `chunk_delta`(공유) + `agent_private_delta`(개인) + `command_result` 이벤트 생성

### 2.5 World/Chunk Directory

- 활성 청크 메타/이웃 링크/점유 상태 관리
- 이웃 청크 생성 시 분산락(`lock:chunk:{id}:dir:{D}`) 적용
- GC 후보 계산 및 링크 해제

### 2.6 Resource Node Service

- 노드 정적 정의(`type, x, y, max_remaining, regen_ticks`) 관리
- 노드 동적 상태(`remaining, state, version`) 관리
- 노드 생성 규칙: reachable floor 인접 wall 셀만 허용
- v1 리소스 타입은 `gold`만 활성화

### 2.7 Pathfinding Service

- 청크 로컬 A* 계산
- 벽 및 점유셀 차단
- 경로 없음(unreachable) 조기 판정

### 2.8 Broadcaster

- 청크별 링버퍼 저장(`event_id={chunk}:{tick}:{seq}`)
- Agent WS와 Spectator SSE/WS로 공유 이벤트 fan-out
- Agent WS + Owner stream 개인 이벤트(`agent_private_delta`) fan-out
- Owner stream으로 tracked agent 전환/개인 상태 fan-out
- Last-Event-ID 기반 replay, 범위 이탈 시 resync 트리거

## 3. Runtime Container/Process View

```mermaid
flowchart TB
    subgraph AppNode[Game Server Node (Uvicorn worker=1)]
        FastAPI[FastAPI App]
        TickLoop[Tick Loop Task]
        WSAgent[Agent WS Handler]
        OwnerHandler[Owner Stream Handler]
        SSEHandler[SSE Handler]
        WSHandler[Spectator WS Handler]

        FastAPI --> WSAgent
        FastAPI --> OwnerHandler
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
- 출력:
  - 공유: `command_challenge`, `command_ack`, `command_result`, `chunk_transition`, `chunk_static`, `chunk_delta`
  - 개인: `agent_private_delta`
- 실패 코드: `auth_failed`, `expired_challenge`, `busy`, `out_of_bounds`, `invalid_cmd`, `rate_limited`, `unreachable`, `node_not_found`, `too_far`, `depleted`, `interrupted_by_new_command`

### 4.2 Spectator Boundary (read-only)

- 입력: 없음(연결 수립 제외)
- 출력: `session_ready`, `chunk_static`, `chunk_delta`, `heartbeat`
- 제한: `agent_private_delta`는 절대 전달하지 않음
- 제한: `chunk_transition`은 기본 spectator 스트림에서 전달하지 않음
- 선택: Spectator WS 허용 시 inbound payload는 drop 또는 연결 종료

### 4.3 Owner Boundary (read-only, tracked agent)

- 입력: 없음(연결 수립 제외)
- 출력: `session_ready`, `chunk_transition`, `chunk_static`, `chunk_delta`, `command_ack`, `command_result`, `agent_private_delta`, `heartbeat`
- 제한: state mutation 불가
- 조건: `role=owner_spectator` + `account owns agent_id` 검증 필수

## 5. Reliability and Backpressure

- Agent 채널은 결과 drop 금지, 과부하 시 연결 종료 후 리싱크
- Owner 채널은 tracked agent 이벤트 drop 금지, 과부하 시 연결 종료 후 리싱크
- Spectator 채널은 오래된 delta drop 허용
- SSE replay 버퍼 권장값: 300 tick(약 60초)

## 6. Extension Slots

- Resource type 확장은 `Resource Node Service`에서 enum/table 확장으로 처리
- Combat/Item/Quest는 Tick Engine 확장 모듈로 분리
- Multi-chunk pathfinding은 Global Navigator 컴포넌트 추가로 확장
- Moderation은 Chat Policy Engine 컴포넌트로 분리 가능

## Revision

| Date | Author | Summary | Impacted Sections |
|---|---|---|---|
| 2026-02-21 | Codex | Owner Plane(read-only tracked stream) 경계와 fan-out 책임을 컴포넌트 설계에 추가 | 1, 2, 4, 5 |
| 2026-02-21 | Codex | gold 자원 노드 서비스와 `agent_private_delta` 경계를 컴포넌트 책임에 추가 | 1, 2, 4 |
| 2026-02-21 | Codex | 백엔드 컴포넌트 책임/경계/프로세스 구조를 상세 정의 | All |
