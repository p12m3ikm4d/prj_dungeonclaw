# Chunk Rendering Contract

본 문서는 프론트엔드가 청크 데이터를 렌더링할 때 필요한 최소 계약을 정의한다.

## 1. 목적

- 백엔드 payload를 UI 요소로 해석하는 규칙을 고정한다.
- MVP 렌더 범위를 `벽/땅/유저/npc` 4가지로 제한한다.
- 프로토콜 변경 없이도 프론트엔드가 데모 청크를 안정적으로 출력하도록 한다.

## 2. 렌더 요소 정의

| Element | Data Source | Rule | Required |
|---|---|---|---|
| floor | `chunk_static.grid[y][x]` | 값이 `0`이면 땅 | Yes |
| wall | `chunk_static.grid[y][x]` | 값이 `1`이면 벽 | Yes |
| user | `chunk_delta.agents[]` | `(x,y)` 좌표에 오버레이 | Yes |
| npc | `chunk_delta.npcs[]` | `(x,y)` 좌표에 오버레이 | Yes (배열 자체), MVP 데이터는 비어있을 수 있음 |

## 3. Payload 계약

### 3.1 `chunk_static`

렌더 기준 필드:

- `grid: int[h][w]`
- `legend: { ".": "floor", "#": "wall" }`
- `render_hint.cell_codes: { "0": "floor", "1": "wall" }`
- `render_hint.agent_overlay: "chunk_delta.agents"`
- `render_hint.npc_overlay: "chunk_delta.npcs"`
- `render_hint.debug_move_default_agent_id: "demo-player"` (dev demo 제어 대상)

규칙:

- MVP는 `grid`를 1차 렌더 소스로 사용한다.
- `tiles`는 원본 디버그/검증용으로만 사용한다.

### 3.2 `chunk_delta`

렌더 기준 필드:

- `agents: [{id, x, y, ...}]`
- `npcs: [{id, x, y, ...}]`

규칙:

- `agents`, `npcs`는 delta 시점의 authoritative 스냅샷으로 간주한다.
- 프론트는 delta 수신 시 이전 오버레이를 교체(replace)한다.
- MVP 현재 상태에서 `npcs`는 빈 배열(`[]`)일 수 있다.

## 4. 좌표와 레이어 규칙

- 좌표는 모두 청크 로컬 좌표(`x,y in [0..49]`)를 사용한다.
- 그리드 인덱싱은 `grid[y][x]`를 따른다.
- 렌더 순서:
1. base tile (`floor` or `wall`)
2. `npc` overlay
3. `user` overlay

충돌 규칙:

- 같은 셀에 `user`와 `npc`가 동시에 존재하면 `user`를 우선 렌더한다.

## 5. 데모 청크 및 디버그 이동

- 데모 관전: `GET /v1/spectate/stream?chunk_id=demo`
- 데모 스냅샷: `GET /v1/chunks/demo/snapshot`
- 레거시 호환 경로: `/api/v1/spectate/stream`, `/api/v1/chunks/{chunk_id}/snapshot`
- 서버는 `chunk_id=demo`를 기본 청크(`chunk-0`)로 정규화한다.
- `chunk-0`은 중앙 원형 홀 + 동/서/남/북 4방향(폭 4셀) 고정 출구 레이아웃을 사용한다.
- 데모 플레이어 id는 `demo-player`로 고정되고, 초기 위치는 `chunk-0` 중앙이다.
- 개발 환경 demo 청크에서는 렌더 검증을 위해 `demo-user-*`, `demo-npc-*` 엔티티가 포함될 수 있다.
- 개발 디버그 클릭 이동: `POST /v1/dev/agent/move-to`, body=`{ "agent_id": "...", "x": int, "y": int }`

## 6. 변경 규칙

- 렌더 요소 추가/삭제 시 `design/protocol.md`, `design/interface.md`, 본 문서를 동시에 갱신한다.
- 프론트가 추가 필드를 요구하면 `.agent/FOR_CODEX.md`로 제안한다.

## Revision

| Date | Author | Summary | Impacted Sections |
|---|---|---|---|
| 2026-02-21 | Codex | 벽/땅/유저/npc 렌더 계약을 별도 문서로 분리하고 demo/debug 연동 규칙을 고정 | All |
| 2026-02-21 | Codex | demo-player 고정 스폰(중앙)과 debug 기본 제어 ID 규약을 추가 | 3.1, 5 |
