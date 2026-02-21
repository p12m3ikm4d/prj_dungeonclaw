# Frontend Architecture Design (MUG)

## 1. Overview
DungeonClaw 프론트엔드는 서버 권위(Server-Authoritative) MUD 데이터를 시각화하는 관전 전용(MUG) 클라이언트로 동작합니다. 모든 상태는 서버가 관리하며, 프론트엔드는 이를 구독하여 화면에 주기적으로 렌더링합니다.

## 2. Tech Stack Strategy (Draft)
- **Framework**: Vite + TypeScript + (React or Vue.js)
- **View Layer**: HTML5 Canvas or CSS Grid (Depending on 50x50 rendering performance requirements)
- **Real-time Comms**: `EventSource` (SSE) mainly.

## 3. Communication Strategy
- **Endpoint**: `/api/v1/spectate`
- **Data Protocol**: `chunk_static` (initial map data) + `chunk_delta` (updates)
- **Replay/Resync**: Handling `Last-Event-ID` upon reconnection.

## 4. Components
- **ChunkViewer**: Main 50x50 map grid.
- **LogViewer**: System logs and event messages stream.
- **AgentStatus**: Currently observed Agent's health, coordinates, etc.
