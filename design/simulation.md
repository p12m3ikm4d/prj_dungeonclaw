# Simulation Design

본 문서는 월드 시뮬레이션의 규칙과 알고리즘을 정의한다.

## 1. Terminology and Constants

- Chunk: 50x50 grid
- Cell local coord: `x,y in [0..49]`
- Tick: fixed-step simulation (`TICK_HZ=5`)
- Move speed: 1 cell/tick
- Occupancy: 1 agent per cell
- Chat scope: chunk
- Block behavior: `failed(blocked)` immediate

## 2. Coordinate and Identity Model

- chunk 식별자: `chunk_id(UUID)`
- 좌표는 항상 청크 로컬 좌표
- 글로벌 좌표 체계는 MVP 제외
- 청크 연결은 neighbor 그래프(`N/E/S/W`)로 표현

## 3. Chunk State Model

필수 필드:
- `chunk_id`
- `tiles_static[50]`
- `neighbors{N,E,S,W}`
- `occupancy[(x,y)->agent_id]`
- `agents[agent_id->Agent]`
- `created_at`, `last_player_left_at`
- `pinned=false`
- `seed:uint64`

## 4. Procedural Generation

### 4.1 Inputs

- `seed`
- `required_edges:Set[Direction]`

### 4.2 Guarantees

1. required edge 진입 셀은 항상 walkable(`.`)
2. required edge 상호 간 연결 경로가 존재
3. 일반 청크 출구 수는 2~4개(입구 포함), 방향당 최대 1개
4. 출구 폭은 기본 4셀

### 4.3 MVP Algorithm

1. 50x50 전체를 `#`로 초기화
2. 내부에 room(직사각) 여러 개를 배치하고 L-자 corridor로 연결
3. required edge를 포함해 총 2~4개 출구 방향을 선택
4. 선택된 방향의 경계에 폭 4셀 출구를 만들고 내부 room network에 연결
5. seed 기반 결정론을 보장하고 required edge 연결성을 유지

### 4.4 Root Chunk (`chunk-0`) Fixed Layout

- 첫 맵(`chunk-0`)은 랜덤이 아닌 고정 규칙을 사용한다.
- 중앙 대형 원형 홀 + 동/서/남/북 4방향 좁은 통로(폭 4셀)를 청크 경계까지 연결한다.
- 관전 데모 기준 맵으로 사용한다.

## 5. Boundary Transition Rules

### 5.1 Trigger

다음 이동 셀이 경계(`x=0|49`, `y=0|49`)이면 전환 판단 수행.

### 5.2 Direction

- `x==0 => W`
- `x==49 => E`
- `y==0 => S`
- `y==49 => N`
- 코너는 이동 벡터 `(dx,dy)`로 결정

### 5.3 Destination Mapping

- W out -> neighbor E edge: `(49, src_y)`
- E out -> neighbor W edge: `(0, src_y)`
- S out -> neighbor N edge: `(src_x, 49)`
- N out -> neighbor S edge: `(src_x, 0)`

### 5.4 Atomicity

- 목적지 점유 시 전환 전체 실패
- 에이전트는 원래 셀 유지
- 커맨드는 즉시 `failed(blocked)`

### 5.5 Missing Neighbor

- 이웃 청크 없으면 새 청크 생성
- `(src_chunk_id, dir)` 단위 락으로 중복 생성 방지

## 6. Tick Engine State Machine

### 6.1 Agent Command State

- `idle`
- `executing`
- `completed`
- `failed`

제약:
- agent당 in-flight 명령 1개
- executing 중 신규 명령은 `busy`

### 6.2 Tick Step Order

1. 신규 승인 커맨드 executing 승격(FIFO)
2. executing 커맨드별 next step 계산
3. 점유/장애물 체크
4. 경계 전환 원자 처리
5. 완료/실패 판정
6. delta/result 이벤트 발행

### 6.3 Deterministic Ordering

- 1차 정렬: `command_accepted_at`
- 2차 정렬: `agent_id`

## 7. Pathfinding

- 알고리즘: grid A*
- 통과 불가: `#`, 현재 점유 셀
- unreachable은 커맨드 시작 시 판정 가능
- 동적 장애물은 실행 중 blocked로 처리

## 8. Chunk GC Rules

### 8.1 Deletion Criteria

- `occupants == 0`
- `now - last_player_left_at >= TTL` (기본 60초)
- `degree <= 1`
- `pinned == false`

### 8.2 Deletion Procedure

1. GC 후보 선정
2. 이웃의 역방향 링크 해제
3. 청크 상태 제거
4. (옵션) tombstone 기록

### 8.3 GC Safety

- active chunk는 GC 대상 제외
- transition 진행 중 chunk는 GC 잠금 상태에서 제외

## 9. Fairness and Rate Policy

- command: in-flight 1 + optional cooldown
- chat: 2초당 1회, 200자
- FIFO로 시작, 운영 데이터로 보정

## 10. Implementation Mapping (FastAPI/Redis/PostgreSQL)

- FastAPI startup에서 tick loop task 시작
- WS Agent handler와 SSE handler를 broadcaster로 분리
- Redis:
  - rate limit
  - chunk neighbor 생성 락
- PostgreSQL:
  - account/key/session
  - run/event/snapshot 메타

## 11. Post-MVP Backlog (Locked Out of Scope)

- 전투/아이템/랭킹은 MVP 범위에서 제외하고, 시뮬레이션 안정화 이후 별도 트랙으로만 진행한다.
- 멀티 청크 global navigation은 도입하지 않으며, MVP는 청크 로컬 `move_to`만 지원한다.
- 교착 해소 액션(`yield/swap/shove`)은 MVP에서 비활성으로 고정한다.
- 대규모 노드 그래프 pathfinding은 단일 청크 A* 운영 한계가 관측된 이후에만 검토한다.

## Revision

| Date | Author | Summary | Impacted Sections |
|---|---|---|---|
| 2026-02-21 | Codex | 시뮬레이션 규칙(생성/전환/틱/경로/GC/공정성)을 상세 설계로 분리 | All |
| 2026-02-21 | Codex | 확장 항목을 Post-MVP 범위 고정 정책으로 전환 | 11 |
| 2026-02-21 | Codex | root 고정 레이아웃(중앙 원형+4방향 출구)과 일반 청크 출구 규칙(2~4개, 폭4)을 반영 | 4 |
