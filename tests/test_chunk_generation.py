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


def _edge_open_positions(tiles: list[str], direction: str) -> list[Cell]:
    height = len(tiles)
    width = len(tiles[0]) if tiles else 0
    if direction == "N":
        y = height - 1
        return [(x, y) for x in range(width) if tiles[y][x] == "."]
    if direction == "S":
        y = 0
        return [(x, y) for x in range(width) if tiles[y][x] == "."]
    if direction == "E":
        x = width - 1
        return [(x, y) for y in range(height) if tiles[y][x] == "."]
    if direction == "W":
        x = 0
        return [(x, y) for y in range(height) if tiles[y][x] == "."]
    raise ValueError(direction)


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

    def test_generation_contains_room_sized_open_area(self) -> None:
        tiles = generate_chunk_tiles(width=50, height=50, seed=20260221, required_edges={"N", "E", "S", "W"})
        has_room = False
        for y in range(1, 46):
            for x in range(1, 46):
                if all(tiles[y + dy][x + dx] == "." for dy in range(4) for dx in range(4)):
                    has_room = True
                    break
            if has_room:
                break
        self.assertTrue(has_room)

    def test_generation_floor_ratio_is_reasonable(self) -> None:
        tiles = generate_chunk_tiles(width=50, height=50, seed=314159, required_edges={"W"})
        floor_cells = sum(ch == "." for row in tiles for ch in row)
        ratio = floor_cells / float(50 * 50)
        self.assertGreater(ratio, 0.25)
        self.assertLess(ratio, 0.65)

    def test_normal_chunk_exit_count_and_width_rules(self) -> None:
        tiles = generate_chunk_tiles(width=50, height=50, seed=20260221, required_edges={"W"})
        active = {
            direction: _edge_open_positions(tiles, direction)
            for direction in ("N", "E", "S", "W")
        }
        open_directions = [direction for direction, cells in active.items() if cells]
        self.assertGreaterEqual(len(open_directions), 2)
        self.assertLessEqual(len(open_directions), 4)
        self.assertIn("W", open_directions)
        for direction in open_directions:
            self.assertEqual(len(active[direction]), 4)

    def test_root_layout_is_fixed_circle_with_four_exits(self) -> None:
        tiles = generate_chunk_tiles(
            width=50,
            height=50,
            seed=1,
            required_edges=set(),
            root_layout=True,
        )
        for direction in ("N", "E", "S", "W"):
            self.assertEqual(len(_edge_open_positions(tiles, direction)), 4)

        cx = 25
        cy = 25
        self.assertEqual(tiles[cy][cx], ".")
        self.assertEqual(tiles[cy][cx + 8], ".")
        self.assertEqual(tiles[cy][cx - 8], ".")
        self.assertEqual(tiles[cy + 8][cx], ".")
        self.assertEqual(tiles[cy - 8][cx], ".")


if __name__ == "__main__":
    unittest.main()
