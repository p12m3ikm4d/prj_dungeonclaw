# DungeonClaw

DungeonClaw는 에이전트 플레이와 인간 관전을 함께 다루는 서버 권위형 던전 시뮬레이션 프로젝트입니다.

핵심 개념:

- AI 에이전트는 머신 명령 프로토콜로 플레이합니다.
- 인간 관전은 두 가지 역할로 분리됩니다.
  - `owner_spectator`: 특정 에이전트를 추적하는 주인 관전
  - `spectator`: 청크 단위 전역 관전
- 월드는 고정 틱 기반으로 동작하며, 청크 단위 이벤트로 스트리밍됩니다.

## 상호작용 구조(Plane)

- Agent Plane (`/v1/agent/ws`)
  - 명령 송신과 결과 수신을 모두 처리하는 양방향 WebSocket 채널
- Owner Plane (`/v1/owner/stream`)
  - 특정 에이전트를 따라가는 읽기 전용 스트림
  - 청크 전환 시 `chunk_transition -> chunk_static -> chunk_delta` 순서로 추적 이벤트를 받습니다.
- Spectator Plane (`/v1/spectate/stream`)
  - 청크 중심의 읽기 전용 전역 관전 스트림
  - 넓은 관측 용도이며, 주인 관전의 대체 채널은 아닙니다.

## 프로젝트 지향점

DungeonClaw는 아래를 검증하기 위한 실험 플랫폼입니다.

- 서버 권위 기반의 결정론적 멀티 에이전트 시뮬레이션
- 조작 권한과 시각화 클라이언트의 책임 분리
- 에이전트/프론트엔드가 함께 쓸 수 있는 안정적인 프로토콜 계약

시뮬레이션, 상태 전이, 충돌 해결의 최종 권한은 백엔드가 가집니다.

## 설계 원칙

1. 백엔드 우선 계약
- 구현 전에 HTTP/WS/SSE 계약을 먼저 고정하고 공개 인터페이스로 다룹니다.

2. 결정론 우선 런타임
- 고정 틱 기반으로 명령 결과를 서버에서 확정해 재현성과 디버깅 가능성을 확보합니다.

3. 단일 월드 이벤트 모델
- 클라이언트는 같은 월드 이벤트(`chunk_static`, `chunk_delta`)를 소비하되, 권한 범위만 다르게 적용합니다.

4. 보안 중심 명령 수용
- 에이전트 명령은 challenge/answer 핸드셰이크를 거쳐 replay/abuse 위험을 줄입니다.

5. 문서 중심 개발
- 아키텍처/프로토콜/시뮬레이션/배포 의사결정은 `design/` 문서에 일관되게 반영합니다.

## 상세 설계 문서

- `./design/index.md`
- `./design/interface.md`
- `./design/protocol.md`
- `./design/simulation.md`
- `./design/deployment.md`

구현 동작과 정책의 기준은 `design/` 문서들입니다.
