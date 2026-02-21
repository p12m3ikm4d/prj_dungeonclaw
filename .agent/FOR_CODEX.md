# FOR_CODEX

프론트엔드(ANTIGRAVITY)에서 백엔드에 요청할 변경사항을 기록하는 문서.

## 작성 규칙

- 새 요청은 `요청 목록` 표에 한 줄 추가
- `Request ID`는 `REQ-YYYYMMDD-###` 형식 사용
- `Status`는 `NEW`로 시작
- 완료/철회된 요청도 삭제하지 않고 상태만 갱신

## 요청 목록

| Request ID | Date | Priority | Title | Required Change | Rationale | Acceptance Criteria | Status |
|---|---|---|---|---|---|---|---|
| REQ-20260221-001 | 2026-02-21 | P0 | Frontend Dev Server 연동 지원 | 1. CORS `http://localhost:5173` 허용<br>2. 개발용 Auth 우회 또는 테스트용 관전자 토큰 발급 지원 | Vite 로컬 환경에서 API/SSE 호출 시 CORS 에러 발생 예상. 로그인 UI 전 빠른 관전 연동 테스트 필요. | FastAPI `allow_origins`에 로컬 호스트 추가 및 임시 테스트 토큰 적용 | ACCEPTED |

## 상태 정의

- `NEW`: 신규 요청
- `IN_REVIEW`: Codex 검토 중
- `ACCEPTED`: 수용
- `CONDITIONAL`: 조건부 수용
- `REJECTED`: 불수용
- `WITHDRAWN`: 요청 철회

## 비고

- 이 파일 변경 시 Codex 검토 대상이 된다.
- 불수용 사유는 `./.agent/FOR_ANTIGRAVITY.md`의 `불수용 기록`에 남긴다.
