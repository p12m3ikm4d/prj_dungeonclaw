from __future__ import annotations

import heapq
from typing import Callable, Dict, List, Optional, Tuple

Cell = Tuple[int, int]


def _heuristic(a: Cell, b: Cell) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _neighbors(cell: Cell, width: int, height: int) -> List[Cell]:
    x, y = cell
    candidates = ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
    return [(nx, ny) for nx, ny in candidates if 0 <= nx < width and 0 <= ny < height]


def astar_path(
    *,
    width: int,
    height: int,
    start: Cell,
    goal: Cell,
    is_blocked: Callable[[Cell], bool],
) -> Optional[List[Cell]]:
    if start == goal:
        return []

    open_heap: List[Tuple[int, int, Cell]] = []
    heapq.heappush(open_heap, (_heuristic(start, goal), 0, start))

    g_score: Dict[Cell, int] = {start: 0}
    came_from: Dict[Cell, Cell] = {}
    serial = 0

    while open_heap:
        _f, _order, current = heapq.heappop(open_heap)
        if current == goal:
            path: List[Cell] = []
            cursor = goal
            while cursor != start:
                path.append(cursor)
                cursor = came_from[cursor]
            path.reverse()
            return path

        for nxt in _neighbors(current, width, height):
            if nxt != goal and is_blocked(nxt):
                continue

            tentative = g_score[current] + 1
            prev = g_score.get(nxt)
            if prev is not None and tentative >= prev:
                continue

            came_from[nxt] = current
            g_score[nxt] = tentative
            serial += 1
            f_score = tentative + _heuristic(nxt, goal)
            heapq.heappush(open_heap, (f_score, serial, nxt))

    return None
