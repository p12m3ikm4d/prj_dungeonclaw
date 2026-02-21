from __future__ import annotations

import random
from typing import Iterable, List, Set, Tuple

Cell = Tuple[int, int]


def _edge_anchor(width: int, height: int, direction: str) -> Cell:
    cx = width // 2
    cy = height // 2
    if direction == "N":
        return (cx, height - 1)
    if direction == "E":
        return (width - 1, cy)
    if direction == "S":
        return (cx, 0)
    if direction == "W":
        return (0, cy)
    raise ValueError(f"invalid direction: {direction}")


def _step_towards(a: Cell, b: Cell) -> Cell:
    ax, ay = a
    bx, by = b
    if ax < bx:
        return (ax + 1, ay)
    if ax > bx:
        return (ax - 1, ay)
    if ay < by:
        return (ax, ay + 1)
    if ay > by:
        return (ax, ay - 1)
    return a


def _carve_line(grid: List[List[str]], start: Cell, end: Cell) -> None:
    cursor = start
    grid[cursor[1]][cursor[0]] = "."
    while cursor != end:
        cursor = _step_towards(cursor, end)
        grid[cursor[1]][cursor[0]] = "."


def generate_chunk_tiles(
    *,
    width: int,
    height: int,
    seed: int,
    required_edges: Iterable[str],
) -> List[str]:
    """
    Generate a deterministic procedural dungeon chunk.

    Guarantees:
    1) Required edge entry cells are walkable.
    2) Required edges are mutually connected through carved corridors.
    3) Spawn corridor near (1,1) remains walkable for deterministic startup.
    """
    rng = random.Random(seed)
    req: Set[str] = {d for d in required_edges if d in {"N", "E", "S", "W"}}

    grid: List[List[str]] = [["#" for _ in range(width)] for _ in range(height)]

    # Keep the outer ring open to simplify boundary transition safety.
    for x in range(width):
        grid[0][x] = "."
        grid[height - 1][x] = "."
    for y in range(height):
        grid[y][0] = "."
        grid[y][width - 1] = "."

    # Interior random carve.
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            grid[y][x] = "." if rng.random() < 0.68 else "#"

    # Deterministic starter corridors for predictable spawn and early movement.
    for x in range(1, width - 1):
        grid[1][x] = "."
    for y in range(1, height - 1):
        grid[y][1] = "."

    # Core room near center.
    cx = width // 2
    cy = height // 2
    for y in range(max(1, cy - 2), min(height - 1, cy + 3)):
        for x in range(max(1, cx - 2), min(width - 1, cx + 3)):
            grid[y][x] = "."

    # Required edge connectivity.
    for direction in sorted(req):
        anchor = _edge_anchor(width, height, direction)
        entry = anchor
        if direction == "N":
            inside = (anchor[0], height - 2)
        elif direction == "E":
            inside = (width - 2, anchor[1])
        elif direction == "S":
            inside = (anchor[0], 1)
        else:  # W
            inside = (1, anchor[1])

        grid[entry[1]][entry[0]] = "."
        grid[inside[1]][inside[0]] = "."
        _carve_line(grid, inside, (cx, cy))

    # Ensure spawn position is walkable.
    if width > 1 and height > 1:
        grid[1][1] = "."

    return ["".join(row) for row in grid]
