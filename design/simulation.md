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
- Harvest range: Manhattan distance `<= 1`
- Resource type(v1): `gold` only (schema는 확장 가능)
- Resource regen: fixed tick rule (`regen_ticks`)

## 2. Coordinate and Identity Model

- chunk 식별자: `chunk_id(UUID)`
- 좌표는 항상 청크 로컬 좌표
- 글로벌 좌표 체계는 MVP 제외
- 청크 연결은 neighbor 그래프(`N/E/S/W`)로 표현
- resource node 식별자: `node_id` (청크 내 unique)

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
- `resource_nodes_static[node_id -> {type, x, y, max_remaining, harvest_ticks_per_unit, regen_ticks}]`
- `resource_nodes_dynamic[node_id -> {remaining, state, version, depleted_at_tick, next_regen_tick}]`

Agent runtime 상태:
- `activity_state: idle | moving | harvesting`
- `inventory.gold: int`
- `active_harvest_node_id?: string`

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

### 4.5 Resource Node Placement (`gold`, v1)

- 자원 노드는 `wall(#)` 셀 위에만 배치한다.
- 단, 아래 조건을 동시에 만족해야 한다.
  1. wall 셀이 최소 1개의 도달 가능한 floor 셀에 인접한다.
  2. 도달 가능한 floor 집합은 출구/중앙 기준 BFS로 계산한다.
- 결과적으로 모든 노드는 플레이어가 근접 1칸 규칙으로 접근 가능해야 한다.
- 노드 수는 구성값으로 관리한다(고정 상수로 하드코딩하지 않음).

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

### 6.1 Agent Activity State

- `idle`
- `moving`
- `harvesting`

제약:
- agent당 in-flight 명령 1개
- `moving` 중 신규 명령은 `busy`
- `harvesting` 중 신규 명령이 승인되면 harvest를 `failed(interrupted_by_new_command)`로 종료 후 새 명령 시작

### 6.2 Tick Step Order

1. 신규 승인 커맨드 executing 승격(FIFO)
2. `move_to` 실행 중인 에이전트 next step 계산
3. 점유/장애물/경계 전환 처리
4. `harvest` 실행 중인 에이전트 채집 진행도 갱신
5. 자원 노드 상태(`remaining`, `state`, `regen`) 갱신
6. 완료/실패 판정
7. `chunk_delta`(공유) + `agent_private_delta`(개인) + `command_result` 발행

### 6.3 Deterministic Ordering

- 1차 정렬: `command_accepted_at`
- 2차 정렬: `agent_id`

## 7. Pathfinding

- 알고리즘: grid A*
- 통과 불가: `#`, 현재 점유 셀
- unreachable은 커맨드 시작 시 판정 가능
- 동적 장애물은 실행 중 blocked로 처리

## 8. Harvest Rules (`gold`, v1)

### 8.1 Command Input

- `harvest(node_id)`

### 8.2 Start Conditions

- 같은 청크에 `node_id` 존재
- 노드 타입은 `gold`
- 노드 상태가 `available`이고 `remaining > 0`
- 에이전트와 노드의 맨해튼 거리 `<= 1`

### 8.3 Progress/Completion

- `harvest_ticks_per_unit` tick마다 `remaining -= 1`, `inventory.gold += 1`
- `remaining == 0`이 되는 즉시 노드는 `depleted`, `next_regen_tick = now + regen_ticks`
- 채집자가 마지막 단위를 채굴해 고갈시킨 경우: `command_result completed(reason=node_depleted)`

### 8.4 Forced End

- 같은 유저의 신규 명령이 승인되면 기존 harvest 종료: `failed(interrupted_by_new_command)`
- 다른 유저가 먼저 노드를 고갈시켜 채집 지속 불가가 되면: `failed(depleted)`
- 위 두 경우 모두 서버가 사용자 입력 없이 종료 이벤트를 발행해야 한다.

### 8.5 Regen

- `tick >= next_regen_tick`이면 노드 `remaining = max_remaining`, `state = available`
- regen은 고정 tick 규칙으로만 동작한다(확률형 regen 미사용)

## 9. Visibility and Channel Policy

- 공유 상태(모든 관전자/유저):
  - 노드 위치/타입(정적)
  - 노드 remaining/state/version(동적)
- 비공개 상태(해당 유저 + owner_spectator tracked stream):
  - 인벤토리(`inventory.gold`)
  - 개인 진행도/개인 보상

전송 원칙:
- 공유 상태 변화는 `chunk_delta`로 브로드캐스트
- 비공개 상태 변화는 Agent WS + owner stream의 `agent_private_delta`로 전송
- global spectator 스트림에는 비공개 상태를 전송하지 않는다.

## 10. Chunk GC Rules

### 10.1 Deletion Criteria

- `occupants == 0`
- `now - last_player_left_at >= TTL` (기본 60초)
- `degree <= 1`
- `pinned == false`

### 10.2 Deletion Procedure

1. GC 후보 선정
2. 이웃의 역방향 링크 해제
3. 청크 상태 제거
4. (옵션) tombstone 기록

### 10.3 GC Safety

- active chunk는 GC 대상 제외
- transition 진행 중 chunk는 GC 잠금 상태에서 제외

## 11. Fairness and Rate Policy

- command: in-flight 1 + optional cooldown
- chat: 2초당 1회, 200자
- harvest 충돌: 동일 tick에서는 deterministic ordering으로 1명만 성공
- FIFO로 시작, 운영 데이터로 보정

## 12. Implementation Mapping (FastAPI/Redis/PostgreSQL)

- FastAPI startup에서 tick loop task 시작
- WS Agent handler, Owner stream handler, Spectator SSE handler를 broadcaster로 분리
- Redis:
  - rate limit
  - chunk neighbor 생성 락
- PostgreSQL:
  - account/key/session
  - run/event/snapshot 메타

## 13. Post-MVP Backlog (Locked Out of Scope)

- 전투/아이템/랭킹은 MVP 범위에서 제외하고, 시뮬레이션 안정화 이후 별도 트랙으로만 진행한다.
- 멀티 청크 global navigation은 도입하지 않으며, MVP는 청크 로컬 `move_to`만 지원한다.
- 교착 해소 액션(`yield/swap/shove`)은 MVP에서 비활성으로 고정한다.
- 대규모 노드 그래프 pathfinding은 단일 청크 A* 운영 한계가 관측된 이후에만 검토한다.

## Revision

| Date | Author | Summary | Impacted Sections |
|---|---|---|---|
| 2026-02-21 | Codex | owner_spectator 추적 채널 정책을 반영해 비공개 상태 전송 대상을 agent+owner로 확정 | 9, 12 |
| 2026-02-21 | Codex | gold 자원 노드(벽 기반 reachable 배치), harvest 상태/종료 규칙, 공개/비공개 전송 정책을 확정 | 1, 3, 4.5, 6, 7, 8 |
| 2026-02-21 | Codex | 시뮬레이션 규칙(생성/전환/틱/경로/GC/공정성)을 상세 설계로 분리 | All |
| 2026-02-21 | Codex | 확장 항목을 Post-MVP 범위 고정 정책으로 전환 | 13 |
| 2026-02-21 | Codex | root 고정 레이아웃(중앙 원형+4방향 출구)과 일반 청크 출구 규칙(2~4개, 폭4)을 반영 | 4 |
