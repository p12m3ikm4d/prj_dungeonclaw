# FOR_ANTIGRAVITY

이 문서는 프론트엔드 작성 에이전트(ANTIGRAVITY)를 위한 협업 가이드다.

## 1) 프로젝트 맥락

- 이 프로젝트의 프론트엔드는 **관전 전용(MUG)** 이다.
- 게임 상태 권위(authoritative state)는 백엔드에 있고, 프론트엔드는 렌더링/표현만 담당한다.
- 프론트엔드에서 게임 상태를 직접 변경하는 요청은 금지한다.

## 2) 반드시 참조할 문서

작업 전 아래 문서를 우선 읽어야 한다.

1. `/Users/songchihyun/repos/prj_dungeonclaw/design/interface.md`
2. `/Users/songchihyun/repos/prj_dungeonclaw/design/protocol.md`
3. `/Users/songchihyun/repos/prj_dungeonclaw/design/component.md`
4. `/Users/songchihyun/repos/prj_dungeonclaw/design/simulation.md`
5. `/Users/songchihyun/repos/prj_dungeonclaw/design/challenge-strategy.md`
6. `/Users/songchihyun/repos/prj_dungeonclaw/design/backlog.md`
7. `/Users/songchihyun/repos/prj_dungeonclaw/design/deployment.md`

## 3) 프론트엔드 작업 원칙

- 관전자 채널은 SSE 우선, 필요 시 read-only WS fallback을 사용한다.
- 메시지 계약은 `chunk_static + chunk_delta`를 기준으로 구현한다.
- 임의 필드 추측 금지: 스키마가 없으면 먼저 요구사항으로 제기한다.
- 성능 최적화는 프로토콜 계약을 깨지 않는 범위에서만 수행한다.

## 4) 백엔드 요구사항 제기 방법 (중요)

프론트엔드 구현 중 백엔드 변경/추가가 필요하면 반드시 아래 파일에 작성한다.

- `/Users/songchihyun/repos/prj_dungeonclaw/.agent/FOR_CODEX.md`

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
- 보안 관련 우회(토큰 생략, challenge 생략, read-only 위반)는 허용하지 않는다.
