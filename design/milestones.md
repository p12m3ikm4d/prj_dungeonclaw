# Milestone Ledger

본 문서는 스프린트 정의(`design/backlog.md`)와 실제 구현 완료 증적(커밋)을 연결하는 기준 문서다.

## 1. Rule of Record

- 스프린트 범위 정의는 `design/backlog.md`를 따른다.
- 스프린트 완료 여부 판정은 본 문서의 `Evidence Commit`을 기준으로 한다.
- 컨텍스트 압축/요약 중 혼선이 발생하면 본 문서를 1차 기준으로 삼는다.

## 2. Milestone Snapshot (2026-02-21)

| Milestone ID | Scope | Status | Evidence Commit | Branch at Completion | Notes |
|---|---|---|---|---|---|
| M0-DESIGN | 설계 산출물 분해 및 구현 지침 정리 | Done | `850204b` | `main` | ERD/Class/Sequence/Component 등 상세 문서 고정 |
| M1-BE-SPRINT1 | Auth + Session + Agent WS Challenge Core | Done | `80be386` | `codex/challenge-core` | `command_req -> challenge -> answer -> ack` 플로우 및 기본 테스트 추가 |
| M2-BE-SPRINT2 | Tick Engine + `move_to` 실행 루프 | Done | `2b12bd0` | `codex/challenge-core` | 5Hz tick, pathfinding, blocked 실패 처리 로직 반영 |
| M3-FE-SPRINT1 | 프론트엔드 초기화 및 Mock 관전 환경 | Done | `d09bc4d` | `antigravity/frontend-init` | Vite/Vue 기반 관전 UI 초기 골격 |
| M4-INTEGRATION-S1 | Sprint1 통합 머지(`develop`) | Done | `d7a4984` | `develop` | codex + antigravity 통합 및 충돌 해소 |
| M5-AGENT-COLLAB | 에이전트 협업 채널 문서 추가 | Done | `99f3356` | `develop` | `.agent/FOR_ANTIGRAVITY.md`, `.agent/FOR_CODEX.md` 추가 |
| M6-BE-SPRINT3 | Boundary + Chunk Lifecycle | Planned | TBD | `develop` (target) | 원자 전환/neighbor lock/GC 구현 예정 |
| M7-BE-SPRINT4 | Spectator Streaming Hardening | Planned | TBD | `develop` (target) | SSE replay/resync 및 read-only 보강 예정 |
| M8-BE-SPRINT5 | Operational Hardening | Planned | TBD | `develop` (target) | rate limit/moderation/운영 복구 절차 점검 예정 |

## 3. Update Procedure

1. 스프린트 종료 커밋(또는 통합 머지 커밋) 해시를 확정한다.
2. 본 문서 `Milestone Snapshot`에 행을 추가 또는 상태를 갱신한다.
3. `design/backlog.md`의 해당 스프린트 상태를 함께 갱신한다.
4. 상태 변경 커밋 메시지는 `docs: update milestone ledger`를 사용한다.

## 4. Decision

- 스프린트 완료 선언은 구두/채팅이 아니라 `Evidence Commit` 등록으로 확정한다.
- `TBD`는 다음 구현 착수 시점에 즉시 해소한다.

## Revision

| Date | Author | Summary | Impacted Sections |
|---|---|---|---|
| 2026-02-21 | Codex | 스프린트별 완료 증적 커밋을 추적하는 마일스톤 원장 문서 신설 | All |
