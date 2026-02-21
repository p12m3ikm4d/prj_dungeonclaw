# Revision Section Guideline

본 문서는 설계 문서 변경 시 `Revision` 섹션 작성 규칙을 정의한다.

## 1. Mandatory Rules

- 모든 설계 문서는 하단에 `## Revision` 섹션을 유지한다.
- 변경 시 기존 이력을 삭제하지 않고 행을 추가한다.
- 날짜는 `YYYY-MM-DD` 형식 사용.
- 요약은 구현 영향 기준으로 작성한다(문장 1개).

## 2. Required Columns

기본 표 컬럼:

- `Date`
- `Author`
- `Summary`
- `Impacted Sections`

권장 확장 컬럼:

- `Compatibility`
- `Follow-up`

## 3. Writing Quality Bar

- `Summary`는 무엇이 왜 바뀌었는지 포함한다.
- `Impacted Sections`는 문서 내 섹션 제목 또는 번호를 명시한다.
- 프로토콜/스키마 변경은 반드시 호환성 영향을 표시한다.

## 4. Example

| Date | Author | Summary | Impacted Sections | Compatibility |
|---|---|---|---|---|
| 2026-02-21 | Codex | SSE replay 정책을 event_id 기반으로 명확화 | 5.4, 5.5 | Backward compatible |

## 5. Automation Update Policy

자동 갱신 작업은 아래를 반드시 수행한다.

1. 변경된 설계 문서를 식별한다.
2. 문서의 `Revision` 섹션에 신규 행을 추가한다.
3. `Summary`에 변경 이유와 영향을 함께 기록한다.
4. 프로토콜/ERD 변경 시 관련 문서 교차 갱신 여부를 확인한다.

## Revision

| Date | Author | Summary | Impacted Sections |
|---|---|---|---|
| 2026-02-21 | Codex | 설계 문서 리비전 섹션 작성 규칙 정의 | All |
