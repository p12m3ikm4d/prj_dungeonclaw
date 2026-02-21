# Frontend Backlog

## Sprint 1: Foundation & Mock Server
- [x] 프론트엔드 프로젝트 초기화 (프레임워크 선정: 예. Vite) (완료: `d09bc4d`)
- [x] Mock 서버/스크립트 통신 환경 구성 (SSE 테스트용) (완료: `d09bc4d`)
- [x] 기본 레이아웃 및 라우팅 설정 (완료: `d09bc4d`)

## Sprint 2: Core Rendering
- [x] Mock 데이터를 활용한 `chunk_static`, `chunk_delta` 처리 로직 구현 (완료: `bc660dc`)
- [x] 상태 관리(Store) 및 SSE 클라이언트 연동 (완료: `bc660dc`)
- [x] 50x50 MUD 맵 뷰어(World Viewer) MVP 렌더링 (완료: `bc660dc`)

## Sprint 3: Integration & Polish
- [x] 백엔드 연동 테스트 (실 서버와 연결) 및 Replay/Resync 구현 (완료: `3c3478d`)
- [x] 에이전트 상태 패널 및 이벤트 로그 UI 완성 (완료: `4235f3d`)
- [x] 시각적 피드백 개선 (이동, 충돌 등 모션 처리) (완료: `4235f3d`)
- [x] Spectator API 라우팅 규약 준수 및 Dev 세션 토큰 발급 (완료: `463fbbc`)

## Sprint 4: Render MVP & Debug Tools
- [x] 데모 청크 렌더 규약 준수 (floor, wall, user, npc 오버레이 적용)
- [x] 개발용 디버그 클릭 이동 기능 구현 (`POST /v1/dev/agent/move-to`) 및 에러 UI 표시

## Sprint 5: Chunk Following & UX Fixes
- [x] 제어 대상(`debugMoveAgentId`)의 `chunk_transition` 이벤트 추적 및 자동 청크 전환 구현
- [x] 제어 대상 캐릭터(플레이어)를 시각적으로 구별 (주황색/골드 색상 및 스프라이트 변경)
- [x] 시스템 로그 컨테이너가 무한히 늘어나는 CSS 레이아웃 버그 수정 (`min-height: 0` 등 스크롤 박스 제어)

## Sprint 6: FOV Camera & Pixel Textures
- [x] 전체 맵 대신 플레이어 중심의 `10x10` FOV 카메라 렌더링 범위 제한 (`viewportBounds` 계산 구현)
- [x] `32x32px` 도트 아트 느낌의 Floor/Wall 렌더링용 임시 SVG 텍스쳐 적용
- [x] 모니터 DPI / 브라우저 해상도에 무관하게 그래픽이 뭉개지지 않도록 CSS 정수 스케일링(`image-rendering: pixelated`) 적용

## Sprint 7: Extract Assets & Fix Chunk Follow
- [x] 임시 SVG 타일 이미지를 별도 에셋 파일(`frontend/src/assets/wall.svg`, `floor.svg`)로 완전 분리.
- [x] **버그 픽스**: 제어 대상이 청크 경계 밖으로 이동하여 `chunk_delta`에서 사라질 경우(Spectator에게 `chunk_transition` 이벤트가 직접 오지 않는 한계 우회), 증발 직전 좌표와 `neighbors` 데이터를 대조해 대상이 이동한 새 청크로 SSE를 자동 전환하도록 방향 추론 로직 구현.
- [x] **UX 보완**: 마우스 클릭 외에도 손쉽게 맵 끝(청크 경계)으로 이동해 전환을 테스트할 수 있도록 WASD 및 방향키(Arrow keys) 키보드 조작 기능 추가.

## Sprint 8: Fixes & Cleanup
- [x] **CSS 수정**: `spectate-view` 컨테이너 높이를 `100vh`로 제한해 시스템 로그가 무한히 커지며 스크롤바를 유발하는 현상 수정
- [x] **버그 픽스**: 제어 대상이 경계를 넘을 때 백엔드에서 발송하는 `chunk_transition` 이벤트의 데이터 구조 오버라이딩(`data.to_chunk_id`) 오류 수정하여 최상위 필드 파싱 적용
- [x] **Cleanup**: 관전자 목적에 어색한 키보드(`WASD`/방향키) 수동 이동 기능(`handleKeyDown`) 전면 삭제

## Sprint 9: Minimap & FOV 15 & Fix Reloading
- [x] **FOV 15 확장**: 기존 10x10이던 플레이어 중심 렌더링 뷰포트를 15x15 크기로 확대 적용
- [x] **버그 픽스**: 청크 경계에서 `x=50` 방향 오버 무빙 클릭 시, 프론트엔드의 추론 기준선(`=== 49`)이 너무 좁아 발동하지 않던 경계 리로드 실패 문제를 범위 기반(`>= 49`) 조건식으로 교체해 해결
- [x] **미니맵 추가**: 우측 사이드 패널의 Agent Status 창 위에, 현재 청크의 50x50 그리드 전체 조감도를 보여주는 디버그용 미니맵(MInimap) 패널 추가 및 플레이어 오버레이 UI 구현
