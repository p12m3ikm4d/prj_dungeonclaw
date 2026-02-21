# FOR_ANTIGRAVITY

이 문서는 프론트엔드 작성 에이전트(ANTIGRAVITY)를 위한 협업 가이드다.

## 1) 프로젝트 맥락

- 이 프로젝트의 프론트엔드는 **관전 전용(MUG)** 이다.
- 게임 상태 권위(authoritative state)는 백엔드에 있고, 프론트엔드는 렌더링/표현만 담당한다.
- 프론트엔드에서 게임 상태를 직접 변경하는 요청은 금지한다.

## 2) 반드시 참조할 문서

작업 전 아래 문서를 우선 읽어야 한다.

1. `./design/interface.md`
2. `./design/protocol.md`
3. `./design/chunk-rendering.md`
4. `./design/component.md`
5. `./design/simulation.md`
6. `./design/challenge-strategy.md`
7. `./design/backlog.md`
8. `./design/deployment.md`

## 3) 프론트엔드 구현 기준 (중요)

- 관전자 채널은 SSE 우선, 필요 시 read-only WS fallback을 사용한다.
- 메시지 계약은 `chunk_static + chunk_delta`를 기준으로 구현한다.
- 임의 필드 추측 금지: 스키마가 없으면 먼저 요구사항으로 제기한다.
- 성능 최적화는 프로토콜 계약을 깨지 않는 범위에서만 수행한다.

### 3.1 던전 렌더 최소 계약 (벽/땅/유저/npc 4요소)

- 초기 데모 렌더는 반드시 아래 4요소만 사용한다.
- `wall`: `chunk_static.grid[y][x] == 1`
- `floor`: `chunk_static.grid[y][x] == 0`
- `user`: `chunk_delta.agents[]`를 같은 좌표계(x, y)로 오버레이
- `npc`: `chunk_delta.npcs[]`를 같은 좌표계(x, y)로 오버레이
- 참조 보조 필드: `chunk_static.render_hint.cell_codes` (`"0" -> "floor"`, `"1" -> "wall"`), `chunk_static.legend` (`"." -> "floor"`, `"#" -> "wall"`)
- `chunk_static.tiles`는 문자열 기반 원본 데이터이며, 렌더 기준은 우선 `grid`로 통일한다.
- `chunk_delta.npcs`는 MVP에서 비어있을 수 있으며(`[]`), 필드 자체는 항상 존재한다고 가정한다.

### 3.2 데모 청크 연결 기준

- 관전 스트림: `GET /v1/spectate/stream?chunk_id=demo`
- 레거시 호환 경로: `GET /api/v1/spectate/stream?chunk_id=demo`
- 스냅샷: `GET /v1/chunks/demo/snapshot` (또는 `/api/v1/chunks/demo/snapshot`)
- 백엔드는 `chunk_id=demo`를 기본 청크(`chunk-0`)로 해석한다.
- `chunk-0`은 중앙 원형 홀 + 동/서/남/북 4방향(폭 4셀) 고정 출구 구조를 사용한다.
- 데모 플레이어(내 캐릭터) id는 `demo-player`로 고정이며, 초기 좌표는 `chunk-0` 중앙이다.
- 기본 제어 대상 id는 `chunk_static.render_hint.debug_move_default_agent_id`로 확인한다.
- dev demo 렌더 검증용으로 `demo-user-*`, `demo-npc-*` 엔티티가 포함될 수 있다.

### 3.3 디버그 클릭 이동 (challenge 생략 경로)

- 프론트엔드에 개발용 디버그 메뉴를 추가한다.
- 셀 클릭 시 아래 엔드포인트로 이동 의도를 전송한다.
- `POST /v1/dev/agent/move-to` (또는 `/api/v1/dev/agent/move-to`)
- 헤더: `Authorization: Bearer <token>`
- 개발 테스트에서는 `Bearer test-spectator-token` 사용 가능
- 요청 본문:

```json
{
  "agent_id": "demo-player",
  "x": 3,
  "y": 1
}
```

- 응답 `accepted=false`면 `reason`을 그대로 UI에 노출해 디버깅 가능하게 한다.
- 이 경로는 challenge 핸드셰이크를 생략하는 개발용이며, 운영 빌드에서 노출하면 안 된다.

## 4) 백엔드 요구사항 제기 방법 (중요)

프론트엔드 구현 중 백엔드 변경/추가가 필요하면 반드시 아래 파일에 작성한다.

- `./.agent/FOR_CODEX.md`

작성 규칙:

- 각 요청은 하나의 항목으로 분리
- 우선순위(`P0/P1/P2`) 명시
- 필요한 API/이벤트/필드/에러코드 명시
- 필요 이유와 UX 영향 명시
- 수용 기준(acceptance criteria) 명시

## 5) Codex 검토 정책

- Codex는 `FOR_CODEX.md` 변경점을 검토한다.
- Codex는 요청을 **수용/조건부 수용/불수용**으로 판단할 수 있다.
- 불수용 시 반드시 본 문서의 `불수용 기록` 섹션에 사유를 남긴다.

## 6) 불수용 기록

| Date | Request ID | Decision | Reason | Action |
|---|---|---|---|---|

## 7) 주의사항

- 백엔드 계약 문서(`design/*.md`)를 직접 임의 수정하지 않는다.
- 요구사항은 먼저 `FOR_CODEX.md`에 제안하고, 검토 결과를 반영한다.
- 일반 경로에서 보안 우회(토큰 생략, challenge 생략, read-only 위반)는 허용하지 않는다.
- 단, `POST /v1/dev/agent/move-to`는 개발 디버그 목적의 예외 경로이며 dev 환경에서만 사용한다.

## 8) 백로그 증적(Proof of Work) 규약

- **작업(Task/Sprint)이나 이슈를 마무리지을 때마다**, 반드시 `frontend/design/backlog.md`의 해당 항목을 `[x]`로 체크한다.
- 단순히 체크만 하지 않고, 완료를 증명할 수 있는 **커밋 해시, 스크린샷 캡처(PR 시), 또는 구체적인 구현 위치**를 함께 기록하여 증적을 남긴다.

## 9) Active Request to ANTIGRAVITY

### Request ID: FE-REQ-2026-02-21-CHUNK-FOLLOW (Priority: P0)

문제:
- 백엔드에서는 경계 이동 시 청크 생성/전환이 동작하지만, 현재 관전 UI에서 제어 대상(`demo-player`)이 청크를 넘으면 화면 반영이 끊기는 것으로 보인다.

요청:
- dev 디버그 이동 기준 제어 대상(`render_hint.debug_move_default_agent_id`)을 추적하는 **follow 동작**을 프론트엔드에 구현한다.
- 제어 대상이 현재 청크에서 사라질 경우, 가능한 범위에서 대상이 위치한 청크를 탐색하고 SSE 구독 청크를 전환한다.
- 최소한 다음 UX를 보장한다:
  - 현재 구독 청크 ID와 제어 대상 ID를 항상 표시
  - 제어 대상이 현재 청크에 없을 때 명확한 상태 메시지 표시
  - 청크 전환 시 로그에 원인과 대상 청크 ID 기록

수용 기준:
- `demo-player`를 청크 경계로 이동시키면, 관전 화면이 수동 새로고침 없이 새 청크 렌더로 이어진다(또는 실패 사유를 명확히 노출).
- 전환 이후 `chunk_static`/`chunk_delta`가 정상 갱신되고 클릭 이동이 계속 동작한다.

백엔드 추가 요구가 필요할 때:
- 프론트 단독으로 안정 구현이 불가능하면, `./.agent/FOR_CODEX.md`에 아래 형식으로 즉시 요청한다.
  - 필요한 이벤트/필드
  - 왜 프론트 단독으로 불가능한지
  - UX 영향
  - acceptance criteria
