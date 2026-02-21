# Branch Policy

본 문서는 Codex(에이전트)와 백엔드 개발자가 함께 작업할 때의 브랜치/커밋/병합 규약을 정의한다.

## 1. Branch Roles

- `main`: 보호 브랜치. 직접 개발 금지, PR 병합 전용.
- `codex/*`: Codex 작업 브랜치.
- `backend/*`: 백엔드(사람) 작업 브랜치.

## 2. Naming Convention

### 2.1 Codex Branch

- 패턴: `codex/<scope>`
- 예시:
  - `codex/challenge-core`
  - `codex/tick-engine`
  - `codex/deploy-hardening`

### 2.2 Backend Branch

- 패턴: `backend/<scope>`
- 예시:
  - `backend/ws-auth`
  - `backend/chunk-gc`
  - `backend/sse-replay`

## 3. Work Unit Rule

- 1 브랜치 = 1 목적(인증/틱/배포/문서 등)
- 대형 작업은 단계별 브랜치로 분리한다.
- unrelated 변경을 한 브랜치에 섞지 않는다.

## 4. Commit Rule

- 커밋 메시지 prefix를 통일한다.
  - `feat:` 기능 추가
  - `fix:` 버그 수정
  - `docs:` 문서 변경
  - `ops:` 배포/운영 변경
  - `refactor:` 리팩터링
- 커밋은 논리 단위로 쪼갠다.

## 5. Merge/PR Rule

- `main`으로의 직접 push를 금지한다.
- PR 머지 조건:
  1. 관련 설계 문서 갱신 완료(`design/*.md`)
  2. 최소 스모크 테스트 통과
  3. 충돌 해결 후 최신 `main` 반영
- PR 설명에는 변경 목적/영향 범위/검증 결과를 포함한다.

## 6. Sync Rule

- 머지 전 최신 `main`을 반영한다.
  - 정책: `rebase` 또는 `merge` 중 팀 합의 방식 사용
- 동시 변경 충돌은 기능 오너가 1차 해소한다.

## 7. Frontend Request Workflow

- 프론트엔드의 백엔드 요구사항은 `.agent/FOR_CODEX.md`로 접수한다.
- Codex는 요청별로 `ACCEPTED`, `CONDITIONAL`, `REJECTED`를 판단한다.
- `REJECTED` 시 `.agent/FOR_ANTIGRAVITY.md`의 `불수용 기록`에 사유를 남긴다.

## 8. Final Decisions

- 브랜치 접두어는 `codex/`, `backend/`로 고정한다.
- `main`은 병합 전용으로 운영한다.
- 프론트엔드 연동 요구는 `.agent/FOR_CODEX.md`를 단일 창구로 사용한다.

## Revision

| Date | Author | Summary | Impacted Sections |
|---|---|---|---|
| 2026-02-21 | Codex | Codex/Backend 협업을 위한 브랜치/커밋/PR/요구사항 연동 규약을 문서화 | All |
