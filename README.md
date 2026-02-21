# DungeonClaw (MUG/MUD Chunk-Crawl)

에이전트가 MUD 데이터로 플레이하고, 인간은 MUG 화면으로 관전만 하는 서버 권위형 던전 크롤 프로젝트입니다.

- Agent Plane: WebSocket 기반 조작(쓰기 가능)
- Spectator Plane: SSE/WS 기반 관전(읽기 전용)
- 월드 구조: 50x50 청크 단위 절차적 생성 + 비활성 청크 GC

현재 저장소 상태는 **설계 중심 단계**이며, 구현은 리뷰 후 별도 지시로 시작합니다.

---

## 문서 구성

설계 문서는 `design/` 폴더로 통합되었습니다.

- `/Users/songchihyun/repos/prj_dungeonclaw/design/index.md`
  - 설계 산출물 인덱스 + legacy 매핑
- `/Users/songchihyun/repos/prj_dungeonclaw/design/component.md`
  - 컴포넌트 구조/경계/배포
- `/Users/songchihyun/repos/prj_dungeonclaw/design/class.md`
  - 도메인/서비스 클래스 설계
- `/Users/songchihyun/repos/prj_dungeonclaw/design/sequence.md`
  - 핵심 시퀀스 플로우
- `/Users/songchihyun/repos/prj_dungeonclaw/design/erd.md`
  - DB ERD + 인덱싱/보관 정책
- `/Users/songchihyun/repos/prj_dungeonclaw/design/protocol.md`
  - API/WS/SSE 메시지 계약
- `/Users/songchihyun/repos/prj_dungeonclaw/design/simulation.md`
  - 틱/청크/경계/GC/경로 규칙
- `/Users/songchihyun/repos/prj_dungeonclaw/design/challenge-strategy.md`
  - challenge 생성/검증/anti-replay/PoW/난이도 정책
- `/Users/songchihyun/repos/prj_dungeonclaw/design/deployment.md`
  - Windows 서버 기준 Docker Compose 배포 전략
- `/Users/songchihyun/repos/prj_dungeonclaw/design/backlog.md`
  - 구현 착수 백로그(스프린트/우선순위/완료조건)
- `/Users/songchihyun/repos/prj_dungeonclaw/design/branch-policy.md`
  - Codex/Backend 브랜치/커밋/PR 협업 규약
- `/Users/songchihyun/repos/prj_dungeonclaw/design/interface.md`
  - 구현용 인터페이스 기준 문서
- `/Users/songchihyun/repos/prj_dungeonclaw/design/revision-guideline.md`
  - 리비전 섹션 작성 규칙

참고 문서(이관):
- `/Users/songchihyun/repos/prj_dungeonclaw/design/architecture.md`
- `/Users/songchihyun/repos/prj_dungeonclaw/design/planning.md`
- `/Users/songchihyun/repos/prj_dungeonclaw/design/design.md` (superseded entry)

배포 자동화 스크립트:
- `/Users/songchihyun/repos/prj_dungeonclaw/deploy/scripts/bootstrap.ps1`
- `/Users/songchihyun/repos/prj_dungeonclaw/deploy/scripts/deploy.ps1`
- `/Users/songchihyun/repos/prj_dungeonclaw/deploy/scripts/update.ps1`
- `/Users/songchihyun/repos/prj_dungeonclaw/deploy/scripts/smoke-test.ps1`
- `/Users/songchihyun/repos/prj_dungeonclaw/deploy/scripts/backup.ps1`

---

## 확정된 기술 방향

- Backend: Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL, Redis
- Real-time:
  - Agent 제어 채널: WebSocket
  - Spectator 관전 채널: SSE 우선(필요 시 read-only WS 대체)
- 시뮬레이션:
  - 50x50 청크
  - 5Hz tick
  - `move_to(x,y)` + 서버 A*
  - 점유 충돌 시 즉시 `failed(blocked)`

---

## 구현 시 작업 지침

### 1) 백엔드 우선

- 프론트엔드는 구상 단계로 두고, 아래 백엔드 경계부터 구현합니다.
  - 인증/세션/API Key
  - Agent WS 핸드셰이크(`command_req -> challenge -> answer -> ack -> result`)
  - Tick engine + chunk directory + boundary transition
  - Spectator SSE 스트림 + replay/resync

### 2) 인터페이스 소스 오브 트루스

- 외부 계약의 기준 문서는 `/Users/songchihyun/repos/prj_dungeonclaw/design/interface.md`입니다.
- 구현 중 계약 변경이 필요하면 먼저 `design/interface.md`를 갱신한 뒤 코드에 반영합니다.

### 3) 권위 상태(authoritative state) 보존

- MVP에서는 Game loop를 단일 worker에서 운영합니다.
- Tick state를 DB에 매틱 동기화하지 않고 메모리 authoritative + 이벤트 브로드캐스트를 유지합니다.

### 4) WS/SSE 신뢰성 우선

- WS: agent command 결과는 drop 없이 보장 전달(재접속/리싱크 포함)
- SSE: spectator는 `Last-Event-ID` 기반 replay와 snapshot 리싱크 지원
- chunk_static + chunk_delta 구조를 공통 payload로 유지

### 5) 품질 게이트

- 경계 전환 원자성(걸친 상태 금지)
- blocked 즉시 실패 처리
- rate limit(명령/채팅) 및 입력 검증
- trace_id 기반 로그/메트릭 수집

---

## 로컬 환경

가상환경은 이미 준비되어 있습니다: `/Users/songchihyun/repos/prj_dungeonclaw/.venv`

```bash
cd /Users/songchihyun/repos/prj_dungeonclaw
source .venv/bin/activate
```

---

## 구현 시작 전 체크리스트

1. `design/interface.md` 기준으로 API/WS/SSE 스키마를 고정했는가
2. tick 처리 순서와 FIFO 규칙을 코드 레벨에서 결정적으로 만들었는가
3. chunk 생성/삭제/링크 해제 규칙을 테스트 케이스로 명시했는가
4. 관전자 채널이 read-only로 강제되는가
5. 설계 변경 시 `design/revision-guideline.md`를 따라 Revision 섹션을 갱신했는가

---

## 배포 시작 명령

```powershell
pwsh ./deploy/scripts/bootstrap.ps1 -DataRoot "D:/srv/dungeonclaw"
pwsh ./deploy/scripts/deploy.ps1
pwsh ./deploy/scripts/smoke-test.ps1
```
