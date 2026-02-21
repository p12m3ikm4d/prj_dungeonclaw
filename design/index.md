# Design Artifact Index

본 문서는 상세 설계 산출물의 인덱스이며, 기존 단일 문서(`design.md`)의 내용을 개별 문서로 분해한 결과를 추적한다.

## 목적

- 백엔드 구현에 직접 사용할 수 있는 설계 산출물을 도메인별로 분리한다.
- 필수 산출물(`erd`, `class`, `sequence`, `component`)을 독립 문서로 유지한다.
- 프로토콜/시뮬레이션/운영 규칙을 별도 문서로 분리해 변경 시 영향 범위를 명확히 한다.

## 산출물 목록

- `design/component.md`: 시스템 컴포넌트/배포/경계/책임
- `design/class.md`: 도메인/애플리케이션 클래스 설계
- `design/sequence.md`: 핵심 런타임 시퀀스(명령/전환/재동기화/GC)
- `design/erd.md`: PostgreSQL 중심 ERD와 물리 모델
- `design/protocol.md`: WS/SSE/HTTP 계약, 메시지 스키마, 에러 코드
- `design/simulation.md`: 틱 엔진, 청크 생성/전환/GC, 경로 탐색, 공정성
- `design/challenge-strategy.md`: challenge 생성/검증/anti-replay/PoW 전략
- `design/deployment.md`: Windows 서버 기준 Docker Compose 배포 전략
- `design/backlog.md`: 구현 착수 백로그(스프린트/우선순위/완료조건)
- `design/milestones.md`: 스프린트 완료 증적(커밋 해시) 마일스톤 원장
- `design/branch-policy.md`: Codex/Backend 협업 브랜치 규약
- `design/revision-guideline.md`: 리비전 섹션 작성 표준
- `design/architecture.md`: 상위 아키텍처 문서(이관)
- `design/planning.md`: 기획 문서(이관)
- `design/interface.md`: 인터페이스 문서(이관)

## Legacy `design.md` 커버리지 매핑

| Legacy Section | 내용 | New Artifact |
|---|---|---|
| 1 | 용어 정의 | `design/simulation.md` (용어/상수), `design/protocol.md` |
| 2 | 핵심 상수 | `design/simulation.md` |
| 3 | 좌표/ID 체계 | `design/simulation.md`, `design/class.md` |
| 4 | 데이터 모델 | `design/class.md`, `design/erd.md` |
| 5 | 절차적 청크 생성 | `design/simulation.md` |
| 6 | 청크 경계 이동 규칙 | `design/simulation.md`, `design/sequence.md` |
| 7 | 틱 엔진/커맨드 상태 머신 | `design/class.md`, `design/simulation.md`, `design/sequence.md` |
| 8 | 경로 탐색 | `design/simulation.md` |
| 9 | 네트워크 프로토콜 | `design/protocol.md`, `design/component.md` |
| 10 | 챌린지 인증 | `design/protocol.md`, `design/sequence.md`, `design/challenge-strategy.md` |
| 11 | 관측 메시지 | `design/protocol.md`, `design/interface.md` |
| 12 | 청크 GC | `design/simulation.md`, `design/sequence.md` |
| 13 | 레이트리밋/공정성 | `design/protocol.md`, `design/simulation.md` |
| 14 | 확장 포인트 | `design/simulation.md`, `design/component.md` |
| 15 | 스펙 결론 | 본 문서 + 각 상세 설계의 결정사항 |
| 16 | 구현 가이드 | `design/component.md`, `design/protocol.md`, `design/simulation.md` |

## 운영 원칙

- 외부 계약 변경은 `design/protocol.md`와 `design/interface.md`를 동시에 갱신한다.
- 도메인 규칙 변경은 `design/simulation.md` 기준으로 결정하고, 영향이 있으면 `design/sequence.md`를 갱신한다.
- 저장소 스키마 변경은 `design/erd.md`를 먼저 갱신한 뒤 구현을 수정한다.

## Revision

| Date | Author | Summary | Impacted Docs |
|---|---|---|---|
| 2026-02-21 | Codex | Legacy `design.md`를 상세 산출물로 분해하고 매핑 인덱스를 생성 | `design/*.md` |
| 2026-02-21 | Codex | challenge 전략 문서를 인덱스와 커버리지 매핑에 추가 | `design/index.md` |
| 2026-02-21 | Codex | 배포 전략 문서와 구현 착수 백로그 문서를 인덱스에 추가 | `design/index.md` |
| 2026-02-21 | Codex | 협업 브랜치 정책 문서를 인덱스에 추가 | `design/index.md` |
| 2026-02-21 | Codex | 마일스톤 원장 문서를 인덱스에 추가 | `design/index.md` |
