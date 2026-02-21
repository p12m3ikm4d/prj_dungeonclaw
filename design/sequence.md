# Sequence Design

본 문서는 핵심 런타임 시퀀스를 정의한다.

## 1. Agent Command Handshake

```mermaid
sequenceDiagram
    autonumber
    participant A as Agent
    participant GW as GameGateway
    participant CC as CommandCoordinator

    A->>GW: command_req(client_cmd_id, move_to)
    GW->>CC: request(agent_id, client_cmd_id, cmd)
    CC-->>GW: challenge(server_cmd_id, nonce, expires_at)
    GW-->>A: command_challenge

    A->>GW: command_answer(server_cmd_id, sig, proof)
    GW->>CC: answer(agent_id, server_cmd_id, sig, proof)
    CC-->>GW: command_ack(accepted=true, started_tick)
    GW-->>A: command_ack
```

## 2. move_to Execution and Blocked Failure

```mermaid
sequenceDiagram
    autonumber
    participant Tick as TickEngine
    participant WD as WorldDirectory
    participant PF as PathfindingService
    participant BC as Broadcaster

    Tick->>PF: find_path(chunk, from, target)
    PF-->>Tick: path[]
    loop each tick
        Tick->>WD: try_occupy(next_cell)
        alt occupied or blocked tile
            WD-->>Tick: fail
            Tick->>BC: publish(command_result failed(blocked))
            Tick->>BC: publish(chunk_delta blocked_event)
            break
        else success
            WD-->>Tick: moved
            Tick->>BC: publish(chunk_delta position_update)
        end
    end
```

## 3. Boundary Transition (Atomic)

```mermaid
sequenceDiagram
    autonumber
    participant Tick as TickEngine
    participant WD as WorldDirectory
    participant R as RedisLock
    participant BC as Broadcaster

    Tick->>WD: detect_boundary(next_cell, vector)
    alt neighbor exists
        WD-->>Tick: neighbor_chunk_id
    else neighbor missing
        Tick->>R: acquire(lock:chunk:{src}:dir:{D})
        Tick->>WD: create_neighbor(src, dir)
        WD-->>Tick: neighbor_chunk_id
        Tick->>R: release()
    end

    Tick->>WD: check_dest_occupancy(neighbor, mapped_dest)
    alt occupied
        WD-->>Tick: blocked
        Tick->>BC: publish(command_result failed(blocked))
    else free
        Tick->>WD: move_agent(src->neighbor, mapped_dest)
        Tick->>BC: publish(chunk_transition)
        Tick->>BC: publish(chunk_static(to_chunk))
        Tick->>BC: publish(chunk_delta)
    end
```

## 4. Spectator SSE Replay/Resync

```mermaid
sequenceDiagram
    autonumber
    participant S as Spectator
    participant GW as SSEHandler
    participant BC as Broadcaster
    participant SS as SnapshotService

    S->>GW: GET /spectate/stream?chunk_id=X (Last-Event-ID)
    GW->>BC: replay(chunk_id, last_event_id)
    alt replay available
        BC-->>GW: events[]
        GW-->>S: replayed chunk_delta stream
    else out of range
        GW->>SS: build_chunk_snapshot(chunk_id)
        SS-->>GW: chunk_static + latest_delta
        GW-->>S: resync_required
        GW-->>S: chunk_static
        GW-->>S: chunk_delta
    end
```

## 5. Chunk GC

```mermaid
sequenceDiagram
    autonumber
    participant Tick as TickEngine
    participant WD as WorldDirectory
    participant BC as Broadcaster

    Tick->>WD: gc_candidates(now)
    WD-->>Tick: [chunk_ids]
    loop each candidate chunk C
        Tick->>WD: unlink_for_gc(C)
        Tick->>WD: delete_chunk(C)
        Tick->>BC: publish(chunk_closed or world_event)
    end
```

## 6. Failure/Retry Notes

- `busy`, `rate_limited`, `unreachable`는 즉시 재시도하지 않고 agent 전략 루프에서 backoff를 적용한다.
- `blocked`는 재탐색 트리거 이벤트로 간주한다.
- SSE 재연결 시 replay 실패가 반복되면 snapshot 기반 리싱크를 강제한다.

## Revision

| Date | Author | Summary | Impacted Sections |
|---|---|---|---|
| 2026-02-21 | Codex | 핵심 런타임 시퀀스(핸드셰이크/실행/전환/replay/GC) 상세화 | All |
