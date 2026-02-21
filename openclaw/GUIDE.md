# OpenClaw Agent Guide (DungeonClaw)

이 문서는 `/Users/songchihyun/repos/prj_dungeonclaw`에서 OpenClaw 에이전트가 일관되게 작업하기 위한 실행 가이드다.

## 1. 목표와 작업 범위

- 이 저장소는 **MUG 관전 + 서버 권위형 DungeonClaw** 프로젝트다.
- 현재는 구현보다 **설계/계약 정합성 유지**가 우선이다.
- 에이전트는 코드 변경 전에 설계 문서를 먼저 확인하고, 계약 위반 가능성을 우선 점검한다.

## 2. 작업 시작 전 필수 문서

최소 아래 문서를 먼저 읽고 작업을 시작한다.

1. `/Users/songchihyun/repos/prj_dungeonclaw/README.md`
2. `/Users/songchihyun/repos/prj_dungeonclaw/design/interface.md`
3. `/Users/songchihyun/repos/prj_dungeonclaw/design/protocol.md`
4. `/Users/songchihyun/repos/prj_dungeonclaw/design/simulation.md`
5. `/Users/songchihyun/repos/prj_dungeonclaw/design/component.md`
6. `/Users/songchihyun/repos/prj_dungeonclaw/design/backlog.md`

## 3. 핵심 개발 원칙

- 서버가 authoritative state를 가진다. 프론트엔드는 관전(read-only) 원칙을 지킨다.
- 외부 계약(API/WS/SSE) 변경이 필요하면 코드보다 먼저 `design/interface.md`를 갱신한다.
- 스키마/이벤트 필드는 추측하지 않는다. 불명확하면 요구사항으로 기록한다.
- 프론트엔드에서 백엔드 변경이 필요하면 `/Users/songchihyun/repos/prj_dungeonclaw/.agent/FOR_CODEX.md`에 요청을 남긴다.

## 4. 구현/검증 기본 루틴

1. 관련 설계 문서에서 기준 계약 확인
2. 최소 범위 코드 수정
3. 테스트/정적 검증 실행
4. 설계 문서 리비전 반영 필요 여부 확인

기본 명령 예시:

```bash
cd /Users/songchihyun/repos/prj_dungeonclaw
source .venv/bin/activate
pytest -q
```

## 5. 커밋 품질 기준

- 변경 이유가 설계 기준과 연결되어야 한다.
- 계약 변경은 문서와 코드가 동시에 정합해야 한다.
- 테스트 불가 시 이유와 리스크를 명시한다.

## 6. OpenClaw Skills 연동 원칙

- 프로젝트 로컬 스킬은 `/Users/songchihyun/repos/prj_dungeonclaw/skills`에 둔다.
- 동일 이름 충돌 시 workspace 스킬이 우선된다.
- 스킬 구조/형식은 `/Users/songchihyun/repos/prj_dungeonclaw/openclaw/SKILLS.md`를 따른다.
