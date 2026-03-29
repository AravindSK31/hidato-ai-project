from __future__ import annotations

import random
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Literal

from hidato_backtracking import (
    HexGrid,
    get_adjacent_coords,
    solve_hidato_grid,
    clone_grid,
)


Coord = Tuple[int, int]
BoardSize = Literal["small", "medium", "large"]
CluePattern = Literal["random", "evenly_spread", "boundary", "center", "clustered_values"]
Difficulty = Literal["easy", "medium", "hard"]


@dataclass
class GeneratedPuzzle:
    puzzle_grid: HexGrid
    solution_grid: HexGrid
    clue_count: int
    clue_ratio: float
    solvable: bool
    board_size: BoardSize
    board_shape: List[int]
    clue_pattern: CluePattern
    difficulty: Difficulty
    generator_seed: Optional[int] = None


# ---------------------------------
# Board shapes
# ---------------------------------

SHAPES: Dict[BoardSize, List[int]] = {
    "small": [3, 4, 5, 4, 3],
    "medium": [4, 5, 6, 5, 4],
    "large": [5, 6, 7, 8, 7, 6, 5],
}


# ---------------------------------
# Basic helpers
# ---------------------------------

def make_empty_grid(row_lengths: List[int]) -> HexGrid:
    return [[None for _ in range(length)] for length in row_lengths]


def all_coords(grid: HexGrid) -> List[Coord]:
    coords: List[Coord] = []
    for r, row in enumerate(grid):
        for c, _ in enumerate(row):
            coords.append((r, c))
    return coords


def count_cells(row_lengths: List[int]) -> int:
    return sum(row_lengths)


def get_boundary_coords(grid: HexGrid) -> List[Coord]:
    coords = all_coords(grid)
    boundary: List[Coord] = []

    for r, c in coords:
        deg = len(get_adjacent_coords(grid, r, c))
        # On these hex-like boards, edge cells typically have smaller degree
        if deg < 6:
            boundary.append((r, c))

    return boundary


def get_center_coords(grid: HexGrid) -> List[Coord]:
    coords = all_coords(grid)
    boundary = set(get_boundary_coords(grid))
    return [coord for coord in coords if coord not in boundary]


def value_positions(grid: HexGrid) -> Dict[int, Coord]:
    pos: Dict[int, Coord] = {}
    for r, row in enumerate(grid):
        for c, value in enumerate(row):
            if value is not None:
                pos[value] = (r, c)
    return pos


# ---------------------------------
# Full-solution generator
# ---------------------------------

def generate_full_solution(
    row_lengths: List[int],
    max_tries: int = 300,
    rng: Optional[random.Random] = None,
) -> Optional[HexGrid]:
    """
    Generate a full valid Hidato solution by finding a Hamiltonian path
    through the hex board and labeling it 1..N.
    """
    if rng is None:
        rng = random.Random()

    grid = make_empty_grid(row_lengths)
    coords = all_coords(grid)
    n = len(coords)

    neighbors: Dict[Coord, List[Coord]] = {
        coord: get_adjacent_coords(grid, coord[0], coord[1]) for coord in coords
    }

    for _ in range(max_tries):
        start = rng.choice(coords)
        visited = {start}
        path = [start]

        if _search_path(start, neighbors, visited, path, n, rng):
            solution = make_empty_grid(row_lengths)
            for value, (r, c) in enumerate(path, start=1):
                solution[r][c] = value
            return solution

    return None


def _search_path(
    current: Coord,
    neighbors: Dict[Coord, List[Coord]],
    visited: set[Coord],
    path: List[Coord],
    target_len: int,
    rng: random.Random,
) -> bool:
    if len(path) == target_len:
        return True

    candidates = [nbr for nbr in neighbors[current] if nbr not in visited]

    # Warnsdorff-style ordering: prefer cells with fewer onward moves
    rng.shuffle(candidates)
    candidates.sort(
        key=lambda cell: sum(1 for nxt in neighbors[cell] if nxt not in visited)
    )

    for nxt in candidates:
        visited.add(nxt)
        path.append(nxt)

        if _search_path(nxt, neighbors, visited, path, target_len, rng):
            return True

        path.pop()
        visited.remove(nxt)

    return False


# ---------------------------------
# Clue selection strategies
# ---------------------------------

def choose_clues_by_pattern(
    solution_grid: HexGrid,
    clues_to_keep: int,
    clue_pattern: CluePattern,
    rng: Optional[random.Random] = None,
) -> List[int]:
    if rng is None:
        rng = random.Random()

    n = get_expected_range(solution_grid)
    pos = value_positions(solution_grid)
    all_values = list(range(1, n + 1))

    # Always keep endpoints
    must_keep = {1, n}

    if clues_to_keep < len(must_keep):
        raise ValueError("clues_to_keep is too small for mandatory clues.")

    remaining_slots = clues_to_keep - len(must_keep)

    if remaining_slots == 0:
        return sorted(must_keep)

    if clue_pattern == "random":
        pool = [v for v in all_values if v not in must_keep]
        rng.shuffle(pool)
        chosen = set(pool[:remaining_slots])

    elif clue_pattern == "evenly_spread":
        chosen = set()
        step = max(1, n // max(1, clues_to_keep - 1))
        candidate_values = list(range(1, n + 1, step))
        candidate_values = [v for v in candidate_values if v not in must_keep]

        for v in candidate_values:
            if len(chosen) < remaining_slots:
                chosen.add(v)

        if len(chosen) < remaining_slots:
            leftovers = [v for v in all_values if v not in must_keep and v not in chosen]
            rng.shuffle(leftovers)
            chosen.update(leftovers[: remaining_slots - len(chosen)])

    elif clue_pattern == "clustered_values":
        # Keep a contiguous-ish chunk of values + endpoints
        segment_len = remaining_slots
        max_start = max(2, n - segment_len)
        start = rng.randint(2, max_start)
        chosen = set(range(start, min(n, start + segment_len)))
        chosen = {v for v in chosen if v not in must_keep}

        if len(chosen) < remaining_slots:
            leftovers = [v for v in all_values if v not in must_keep and v not in chosen]
            rng.shuffle(leftovers)
            chosen.update(leftovers[: remaining_slots - len(chosen)])

    elif clue_pattern in ("boundary", "center"):
        boundary_coords = set(get_boundary_coords(solution_grid))
        center_coords = set(get_center_coords(solution_grid))

        if clue_pattern == "boundary":
            preferred_values = [
                v for v in all_values
                if v not in must_keep and pos[v] in boundary_coords
            ]
            fallback_values = [
                v for v in all_values
                if v not in must_keep and pos[v] not in boundary_coords
            ]
        else:
            preferred_values = [
                v for v in all_values
                if v not in must_keep and pos[v] in center_coords
            ]
            fallback_values = [
                v for v in all_values
                if v not in must_keep and pos[v] not in center_coords
            ]

        rng.shuffle(preferred_values)
        rng.shuffle(fallback_values)

        chosen = set(preferred_values[:remaining_slots])

        if len(chosen) < remaining_slots:
            chosen.update(fallback_values[: remaining_slots - len(chosen)])

    else:
        raise ValueError(f"Unsupported clue pattern: {clue_pattern}")

    final_values = sorted(must_keep | chosen)
    return final_values


def make_puzzle_from_kept_values(solution_grid: HexGrid, kept_values: List[int]) -> HexGrid:
    keep_set = set(kept_values)
    puzzle = clone_grid(solution_grid)

    for r, row in enumerate(puzzle):
        for c, value in enumerate(row):
            if value not in keep_set:
                puzzle[r][c] = None

    return puzzle


# ---------------------------------
# Difficulty logic
# ---------------------------------

def get_expected_range(grid: HexGrid) -> int:
    return sum(len(row) for row in grid)


def classify_difficulty(
    board_size: BoardSize,
    clue_ratio: float,
    clue_pattern: CluePattern,
) -> Difficulty:
    """
    Rule-based difficulty classification.

    Easier:
    - smaller board
    - higher clue ratio
    - evenly spread clues

    Harder:
    - larger board
    - lower clue ratio
    - clustered or structurally harder patterns
    """
    score = 0

    # board size contribution
    if board_size == "small":
        score += 1
    elif board_size == "medium":
        score += 2
    else:
        score += 3

    # clue ratio contribution
    if clue_ratio >= 0.45:
        score += 1
    elif clue_ratio >= 0.30:
        score += 2
    else:
        score += 3

    # clue pattern contribution
    if clue_pattern == "evenly_spread":
        score += 1
    elif clue_pattern in ("random", "boundary", "center"):
        score += 2
    else:  # clustered_values
        score += 3

    if score <= 4:
        return "easy"
    elif score <= 6:
        return "medium"
    return "hard"


# ---------------------------------
# Puzzle generation with variation
# ---------------------------------

def generate_variant_puzzle(
    board_size: BoardSize,
    clue_ratio: float,
    clue_pattern: CluePattern,
    seed: Optional[int] = None,
    max_solution_tries: int = 300,
    max_puzzle_tries: int = 120,
) -> GeneratedPuzzle:
    rng = random.Random(seed)

    row_lengths = SHAPES[board_size]
    total_cells = count_cells(row_lengths)
    clues_to_keep = max(2, round(total_cells * clue_ratio))

    solution = generate_full_solution(
        row_lengths=row_lengths,
        max_tries=max_solution_tries,
        rng=rng,
    )
    if solution is None:
        raise RuntimeError("Could not generate a full valid Hidato solution.")

    for _ in range(max_puzzle_tries):
        kept_values = choose_clues_by_pattern(
            solution_grid=solution,
            clues_to_keep=clues_to_keep,
            clue_pattern=clue_pattern,
            rng=rng,
        )
        puzzle = make_puzzle_from_kept_values(solution, kept_values)

        result = solve_hidato_grid(puzzle)
        if result.success:
            actual_clue_count = sum(
                1 for row in puzzle for cell in row if cell is not None
            )
            actual_clue_ratio = actual_clue_count / total_cells
            difficulty = classify_difficulty(
                board_size=board_size,
                clue_ratio=actual_clue_ratio,
                clue_pattern=clue_pattern,
            )

            return GeneratedPuzzle(
                puzzle_grid=puzzle,
                solution_grid=solution,
                clue_count=actual_clue_count,
                clue_ratio=actual_clue_ratio,
                solvable=True,
                board_size=board_size,
                board_shape=row_lengths,
                clue_pattern=clue_pattern,
                difficulty=difficulty,
                generator_seed=seed,
            )

    raise RuntimeError("Could not generate a solvable puzzle for this variation.")


# ---------------------------------
# Convenience difficulty presets
# ---------------------------------

def generate_by_difficulty(
    difficulty: Difficulty,
    seed: Optional[int] = None,
) -> GeneratedPuzzle:
    """
    High-level presets.

    easy   -> smaller board, higher clues, easier patterns
    medium -> moderate mix
    hard   -> larger/sparser/harder patterns
    """
    rng = random.Random(seed)

    if difficulty == "easy":
        board_size: BoardSize = rng.choice(["small", "medium"])
        clue_ratio = rng.uniform(0.42, 0.58)
        clue_pattern: CluePattern = rng.choice(["random", "evenly_spread", "boundary"])

    elif difficulty == "medium":
        board_size = rng.choice(["medium", "large"])
        clue_ratio = rng.uniform(0.28, 0.42)
        clue_pattern = rng.choice(["random", "center", "boundary", "evenly_spread"])

    else:  # hard
        board_size = rng.choice(["medium", "large"])
        clue_ratio = rng.uniform(0.18, 0.30)
        clue_pattern = rng.choice(["clustered_values", "random", "center"])

    return generate_variant_puzzle(
        board_size=board_size,
        clue_ratio=clue_ratio,
        clue_pattern=clue_pattern,
        seed=seed,
    )


# ---------------------------------
# Printing helpers
# ---------------------------------

def print_grid(grid: HexGrid) -> None:
    for row in grid:
        print(" ".join("." if v is None else f"{v:2d}" for v in row))


# ---------------------------------
# Example run
# ---------------------------------

if __name__ == "__main__":
    print("\n=== Difficulty-based generation ===")
    generated = generate_by_difficulty("easy", seed=42)

    print(f"Difficulty: {generated.difficulty}")
    print(f"Board size: {generated.board_size}")
    print(f"Board shape: {generated.board_shape}")
    print(f"Clue pattern: {generated.clue_pattern}")
    print(f"Clue count: {generated.clue_count}")
    print(f"Clue ratio: {generated.clue_ratio:.2f}")
    print(f"Solvable: {generated.solvable}")

    print("\nPuzzle grid:")
    print_grid(generated.puzzle_grid)

    print("\nSolution grid:")
    print_grid(generated.solution_grid)

    print("\n=== Custom variation generation ===")
    custom = generate_variant_puzzle(
        board_size="large",
        clue_ratio=0.22,
        clue_pattern="clustered_values",
        seed=7,
    )

    print(f"Difficulty: {custom.difficulty}")
    print(f"Board size: {custom.board_size}")
    print(f"Board shape: {custom.board_shape}")
    print(f"Clue pattern: {custom.clue_pattern}")
    print(f"Clue count: {custom.clue_count}")
    print(f"Clue ratio: {custom.clue_ratio:.2f}")

    print("\nCustom puzzle grid:")
    print_grid(custom.puzzle_grid)