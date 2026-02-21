import unittest
from collections import deque
from typing import Set, Tuple

from app.services.chunk_generation import generate_chunk_tiles

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
    raise ValueError(direction)


def _neighbors(width: int, height: int, cell: Cell):
    x, y = cell
    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
        if 0 <= nx < width and 0 <= ny < height:
            yield (nx, ny)


class ChunkGenerationTests(unittest.TestCase):
    def test_required_edge_entries_are_walkable(self) -> None:
        width = 50
        height = 50
        required = {"N", "E", "S", "W"}
        tiles = generate_chunk_tiles(
            width=width,
            height=height,
            seed=123456,
            required_edges=required,
        )
        for direction in required:
            x, y = _edge_anchor(width, height, direction)
            self.assertEqual(tiles[y][x], ".")

    def test_required_edges_are_connected(self) -> None:
        width = 50
        height = 50
        required = ["N", "E", "S", "W"]
        tiles = generate_chunk_tiles(
            width=width,
            height=height,
            seed=424242,
            required_edges=required,
        )

        start = _edge_anchor(width, height, required[0])
        queue = deque([start])
        visited: Set[Cell] = {start}

        while queue:
            current = queue.popleft()
            for nxt in _neighbors(width, height, current):
                nx, ny = nxt
                if nxt in visited:
                    continue
                if tiles[ny][nx] != ".":
                    continue
                visited.add(nxt)
                queue.append(nxt)

        for direction in required[1:]:
            self.assertIn(_edge_anchor(width, height, direction), visited)

    def test_generation_is_deterministic_for_seed(self) -> None:
        a = generate_chunk_tiles(width=50, height=50, seed=77, required_edges={"W"})
        b = generate_chunk_tiles(width=50, height=50, seed=77, required_edges={"W"})
        c = generate_chunk_tiles(width=50, height=50, seed=78, required_edges={"W"})

        self.assertEqual(a, b)
        self.assertNotEqual(a, c)


if __name__ == "__main__":
    unittest.main()
