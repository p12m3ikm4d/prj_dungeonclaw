# Sequence Design

본 문서는 핵심 런타임 시퀀스를 정의한다.

## 1. Agent Command Handshake

```mermaid
sequenceDiagram
    autonumber
    participant A as Agent
    participant GW as GameGateway
    participant CC as CommandCoordinator

    A->>GW: command_req(client_cmd_id, harvest)
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

## 3. Harvest Execution (Gold, Shared + Private)

```mermaid
sequenceDiagram
    autonumber
    participant Tick as TickEngine
    participant RS as ResourceNodeService
    participant BC as Broadcaster

    Tick->>RS: validate(node_id, range<=1, available)
    RS-->>Tick: ok

    loop every tick
        Tick->>RS: progress_harvest(agent_id, node_id)
        RS-->>Tick: mined?(amount=1 or 0), remaining
        alt mined amount=1
            Tick->>BC: publish(chunk_delta resource_harvest + remaining)
            Tick->>BC: publish_private(agent_private_delta inventory.gold+1)
        end
        alt remaining == 0
            Tick->>BC: publish(chunk_delta resource_depleted)
            Tick->>BC: publish(command_result completed(node_depleted))
            break
        end
    end
```

## 4. Harvest Forced End by New Command

```mermaid
sequenceDiagram
    autonumber
    participant A as Agent
    participant CC as CommandCoordinator
    participant Tick as TickEngine
    participant BC as Broadcaster

    A->>CC: request(new command)
    CC->>Tick: interrupt_harvest(agent_id)
    Tick->>BC: publish(command_result failed(interrupted_by_new_command))
    CC-->>A: command_ack(accepted=true, started_tick)
```

## 5. Harvest Forced End by External Depletion

```mermaid
sequenceDiagram
    autonumber
    participant Tick as TickEngine
    participant RS as ResourceNodeService
    participant BC as Broadcaster

    Tick->>RS: check node remaining
    RS-->>Tick: depleted by other agent
    Tick->>BC: publish(command_result failed(depleted))
```

## 6. Boundary Transition (Atomic)

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

## 7. Owner Stream Auto-follow

```mermaid
sequenceDiagram
    autonumber
    participant O as Owner UI
    participant GW as OwnerStreamHandler
    participant Tick as TickEngine
    participant BC as Broadcaster

    O->>GW: GET /owner/stream?agent_id=A
    GW->>Tick: bind_owner(agent_id=A, account_id)
    Tick-->>GW: session_ready + initial chunk_static/delta
    GW-->>O: session_ready, chunk_static, chunk_delta

    Tick->>BC: publish(chunk_transition for agent A)
    Tick->>BC: publish(chunk_static destination)
    Tick->>BC: publish(chunk_delta destination)
    Tick->>BC: publish_private(agent_private_delta for A)
    BC-->>O: chunk_transition -> chunk_static -> chunk_delta -> agent_private_delta
```

## 8. Spectator SSE Replay/Resync

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

## 9. Chunk GC

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

## 10. Failure/Retry Notes

- `busy`, `rate_limited`, `unreachable`, `too_far`는 즉시 재시도하지 않고 agent 전략 루프에서 backoff를 적용한다.
- `blocked`, `depleted`는 재탐색/재선택 트리거 이벤트로 간주한다.
- `interrupted_by_new_command`는 오류가 아니라 정상 제어 흐름 중단 코드로 취급한다.
- SSE 재연결 시 replay 실패가 반복되면 snapshot 기반 리싱크를 강제한다.

## Revision

| Date | Author | Summary | Impacted Sections |
|---|---|---|---|
| 2026-02-21 | Codex | Owner stream 자동 추적 시퀀스(`chunk_transition -> chunk_static -> chunk_delta`)를 추가 | 7, 10 |
| 2026-02-21 | Codex | harvest 실행/중단/외부 소진 종료 시퀀스와 private delta 발행 흐름을 추가 | 1, 3, 4, 5, 10 |
| 2026-02-21 | Codex | 핵심 런타임 시퀀스(핸드셰이크/실행/전환/replay/GC) 상세화 | All |
