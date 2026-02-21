# Branch Policy

본 문서는 Codex(에이전트), Antigravity(에이전트), 백엔드 개발자가 함께 작업할 때의 브랜치/커밋/병합 규약을 정의한다.

## 1. Branch Roles

- `main`: 보호 브랜치. 운영/릴리스 반영 전용, 직접 개발 금지.
- `develop`: 통합 개발 브랜치. 기능 브랜치의 기본 PR 대상.
- `codex/*`: 백엔드 작업용 AI 에이전트(Codex) 브랜치.
- `antigravity/*`: 프론트엔드 작업용 AI 에이전트(Antigravity) 브랜치.
- `backend/*`: 백엔드(사람) 작업 브랜치.

## 2. Naming Convention

### 2.1 Integration Branch

- 고정 브랜치: `main`, `develop`

### 2.2 Codex Branch (Backend AI)

- 패턴: `codex/<scope>`
- 예시:
  - `codex/challenge-core`
  - `codex/tick-engine`

### 2.3 Antigravity Branch (Frontend AI)

- 패턴: `antigravity/<scope>`
- 예시:
  - `antigravity/frontend-init`
  - `antigravity/mug-viewer`
  - `antigravity/mock-server`

### 2.4 Backend Branch

- 패턴: `backend/<scope>`
- 예시:
  - `backend/ws-auth`
  - `backend/chunk-gc`
  - `backend/sse-replay`

## 3. Work Unit Rule

- 1 브랜치 = 1 목적(인증/틱/배포/문서 등)
- 대형 작업은 단계별 브랜치로 분리한다.
- unrelated 변경을 한 브랜치에 섞지 않는다.
- 기능 브랜치는 시작 시점에 최신 `develop`에서 분기한다.

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
- `develop`으로의 직접 push를 지양하고 PR 기반 병합을 원칙으로 한다.
- 기능 브랜치(`codex/*`, `antigravity/*`, `backend/*`)는 `develop`으로 PR 한다.
- 릴리스 반영은 `develop -> main` PR로만 진행한다.
- PR 머지 조건:
  1. 관련 설계 문서 갱신 완료(`design/*.md`)
  2. 최소 스모크 테스트 통과
  3. 충돌 해결 후 최신 기준 브랜치 반영
     - 기능 PR: 최신 `develop` 반영
     - 릴리스 PR(`develop -> main`): 최신 `main` 반영
- PR 설명에는 변경 목적/영향 범위/검증 결과를 포함한다.

## 6. Sync Rule

- 기능 브랜치는 머지 전 최신 `develop`을 반영한다.
- `develop`을 `main`에 반영하기 전, 최신 `main`과의 차이를 점검한다.
- 반영 정책은 `rebase` 또는 `merge` 중 팀 합의 방식을 사용한다.
- 동시 변경 충돌은 기능 오너가 1차 해소한다.

## 7. Frontend Request Workflow

- 프론트엔드의 백엔드 요구사항은 `.agent/FOR_CODEX.md`로 접수한다.
- Codex는 요청별로 `ACCEPTED`, `CONDITIONAL`, `REJECTED`를 판단한다.
- `REJECTED` 시 `.agent/FOR_ANTIGRAVITY.md`의 `불수용 기록`에 사유를 남긴다.

## 8. Final Decisions

- 브랜치 접두어는 `codex/`, `antigravity/`, `backend/`로 고정한다.
- 개발 통합은 `develop`, 운영 반영은 `main`으로 분리 운영한다.
- 기능 브랜치의 기본 PR 대상은 `develop`이다.
- 프론트엔드 연동 요구는 `.agent/FOR_CODEX.md`를 단일 창구로 사용한다.

## Revision

| Date | Author | Summary | Impacted Sections |
|---|---|---|---|
| 2026-02-21 | Codex | Codex/Backend 협업을 위한 브랜치/커밋/PR/요구사항 연동 규약을 문서화 | All |
| 2026-02-21 | Antigravity | 프론트엔드 에이전트용 브랜치(`antigravity/*`) 규약 추가 | 1, 2, 8 |
| 2026-02-21 | Codex | `develop` 통합 브랜치 중심의 분기/PR/동기화 규약 추가 | 1, 2, 3, 5, 6, 8 |
