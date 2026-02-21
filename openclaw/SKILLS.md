# OpenClaw Skills Guide (DungeonClaw)

참고 문서: [OpenClaw Skills](https://docs.openclaw.ai/tools/skills)

## 1. 목적

DungeonClaw 작업을 반복 가능하게 만들기 위해, OpenClaw 스킬 작성 규칙과 프로젝트 권장 스킬을 정의한다.

## 2. OpenClaw 스킬 핵심 규칙

- 스킬은 폴더 단위이며 최소 `SKILL.md`가 필요하다.
- `SKILL.md`는 YAML frontmatter에 `name`, `description`을 반드시 포함한다.
- frontmatter key/value는 단일 라인으로 유지한다.
- `metadata`는 단일 라인 JSON 객체를 사용한다.
- 스킬 본문에서 로컬 파일 경로는 `{baseDir}`를 활용해 참조한다.

최소 템플릿:

```md
---
name: dungeonclaw-sample
description: Validate DungeonClaw contracts before implementation.
metadata: {"openclaw":{"requires":{"bins":["rg"]}}}
---

# When to use
Use this skill when the user asks for contract-safe implementation.

# Steps
1. Read `/Users/songchihyun/repos/prj_dungeonclaw/design/interface.md`.
2. Diff proposed changes against the interface contract.
3. Apply minimal edits and run tests.
```

## 3. 저장 위치와 우선순위

OpenClaw는 아래 순서로 스킬을 로드한다.

1. Bundled skills
2. `~/.openclaw/skills`
3. `<workspace>/skills` (최우선)

이 프로젝트에서는 `<workspace>/skills`를 기본 사용한다.

## 4. DungeonClaw 권장 스킬 목록

### 4.1 `dungeonclaw-contract-guard`

- 목적: 코드 변경 전 `design/interface.md` 및 `design/protocol.md` 계약 점검
- 트리거 예시: "계약 안 깨고 WS 이벤트 추가해줘"

### 4.2 `dungeonclaw-simulation-check`

- 목적: tick/chunk/boundary/GC 변경 시 `design/simulation.md` 정합성 검증
- 트리거 예시: "청크 경계 이동 로직 구현해줘"

### 4.3 `dungeonclaw-frontend-readonly`

- 목적: 프론트엔드가 read-only 관전 원칙을 위반하지 않도록 검토
- 트리거 예시: "프론트에서 게임 상태 업데이트하자"

## 5. 스킬 생성 절차

1. `/Users/songchihyun/repos/prj_dungeonclaw/skills/<skill-name>/SKILL.md` 생성
2. frontmatter(`name`, `description`) 작성
3. 필요 시 `metadata.openclaw.requires`로 환경/bin 조건 선언
4. 샘플 요청으로 동작 확인
5. 세션 재시작 또는 skills refresh로 반영

## 6. 보안/운영 주의사항

- 서드파티 스킬은 신뢰하지 말고 내용을 검토한 뒤 활성화한다.
- `skills.entries.*.env`/`apiKey` 값은 로그/프롬프트에 노출하지 않는다.
- 위험 명령 실행형 스킬은 샌드박스 환경에서 우선 검증한다.
