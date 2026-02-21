# Implementation Backlog (Kickoff)

본 백로그는 현재 설계 산출물을 기준으로 구현 착수 순서를 고정한다.

## 0.1 Status Snapshot (2026-02-21)

| Sprint | Status | Notes |
|---|---|---|
| Sprint 0 | Done | infra/skeleton 완료 (마일스톤 원장 참조) |
| Sprint 1 | Done | Auth + Session + Challenge core 완료 |
| Sprint 2 | Done | Tick + `move_to` 완료 |
| Sprint 3 | Done | Boundary + Chunk lifecycle 완료 |
| Sprint 4 | Done (P0) | Spectator SSE/Replay/Resync 완료, WS fallback은 보류 |
| Sprint 5 | Planned | 운영 하드닝(rate limit/moderation/ops) |
| Sprint 6 | In Progress | Owner Spectator stream + Agent 추적 동기화 |

## 0. Progress Snapshot Rule

- 스프린트 정의는 본 문서를 기준으로 유지한다.
- 스프린트 완료 증적(커밋 해시)은 `design/milestones.md`를 기준으로 관리한다.
- `Done` 선언은 마일스톤 원장에 `Evidence Commit`이 등록된 시점으로 본다.

## 1. Sprint 0 (Infrastructure and Skeleton)

### P0

- FastAPI 프로젝트 스켈레톤 생성
- SQLAlchemy/Alembic 초기화
- Redis/Postgres 연결 모듈 구축
- `/healthz` 기본 엔드포인트 구현
- Docker image 빌드 파이프라인 구성(`APP_IMAGE`로 배포 가능 상태)

### Exit Criteria

- `docker compose`에서 실제 backend 컨테이너가 올라오고 `/healthz`가 200 응답

## 2. Sprint 1 (Auth + Session + Challenge Core)

### P0

- `POST /v1/signup`, `POST /v1/keys`, `POST /v1/sessions`
- API key hash 저장/검증
- Agent WS 연결 + session scope 검증
- `command_req -> challenge -> answer -> ack` 구현
- `challenge-strategy.md`의 서명 canonical/pipeline 구현

### P1

- invalid/expired 카운터 기반 cooldown
- challenge observability metric/log 추가

### Exit Criteria

- 정상 challenge 통과/실패 케이스 자동 테스트 통과

## 3. Sprint 2 (Tick Engine + move_to)

### P0

- Chunk 50x50 상태 모델
- A* pathfinding
- 5Hz tick loop
- in-flight 1 커맨드 제약
- `failed(blocked)` 처리

### Exit Criteria

- 단일 청크에서 이동/충돌/실패가 결정론적으로 재현됨

## 4. Sprint 3 (Boundary + Chunk Lifecycle)

### P0

- 경계 이동 원자 전환
- neighbor 생성 락(Redis)
- chunk_static/chunk_delta 송신
- GC 조건/삭제 절차 구현

### Exit Criteria

- 전환 실패 시 원위치 보장, GC 이후 재진입 시 신규 청크 생성 확인

## 5. Sprint 4 (Spectator Streaming)

### P0

- SSE 스트림 `session_ready -> chunk_static -> chunk_delta`
- Last-Event-ID replay + out-of-range resync
- read-only enforcement

### P1

- Spectator WS fallback(read-only)

### Exit Criteria

- 재연결 시 replay/resync 자동 동작

## 6. Sprint 5 (Operational Hardening)

### P0

- rate limit(명령/채팅)
- moderation(금칙어 + 3회 위반 10분 mute)
- metrics/log 대시보드 초안
- backup/restore 리허설

### Exit Criteria

- 운영 체크리스트 통과(배포/업데이트/복구/모니터링)

## 7. Sprint 6 (Owner Spectator Follow Plane)

### P0

- `POST /v1/sessions`에서 `role=owner_spectator` 발급/검증 지원
- `GET /v1/owner/stream?agent_id={id}` SSE 구현(read-only)
- owner stream에 tracked agent 이벤트(`chunk_transition`, `chunk_static`, `chunk_delta`, `command_*`) 전달
- owner stream과 global spectator 권한 경계 분리(전자는 tracked/private 포함, 후자는 공유 이벤트만)
- owner stream 자동 추적(청크 전환 시 재구독 없이 destination payload 연속 수신)

### P1

- `GET /v1/owner/ws?agent_id={id}` fallback 구현
- owner stream replay/resync 정책 정교화

### Exit Criteria

- tracked agent가 경계를 넘어가도 owner UI가 수동 재연결 없이 전환 이벤트를 연속 수신
- global spectator에는 `chunk_transition`/private 이벤트가 노출되지 않음

## 8. Technical Debt Queue

- event_log/snapshot 저장 정책 정밀화
- 샤딩 라우팅 구현(`hash(chunk_id) % shard_count`)
- SDK/CLI 테스트 하네스

## 9. Final Decisions

- 구현 우선순위는 `challenge -> tick -> boundary -> stream -> hardening` 순서로 고정한다.
- 프론트엔드 구현은 본 백로그 범위에서 제외한다.
- 현재 구현 착수 트랙은 Sprint 6(P0)으로 고정한다.

## Revision

| Date | Author | Summary | Impacted Sections |
|---|---|---|---|
| 2026-02-21 | Codex | 스프린트 상태 스냅샷과 Owner Spectator 구현 스프린트(Sprint 6)를 추가하고 착수 트랙을 명시 | 0.1, 7, 9 |
| 2026-02-21 | Codex | 설계 완료 이후 구현 착수용 백로그(스프린트/우선순위/완료조건) 작성 | All |
| 2026-02-21 | Codex | 스프린트 완료 판정 기준을 마일스톤 원장 연동 방식으로 명확화 | 0 |
