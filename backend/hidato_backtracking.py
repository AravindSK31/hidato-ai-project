from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import time


Coord = Tuple[int, int]
HexGrid = List[List[Optional[int]]]


# -----------------------------
# Data model
# -----------------------------

@dataclass
class Cell:
    cell_id: str
    row: int
    col: int
    value: Optional[int]
    fixed: bool
    neighbors: List[str] = field(default_factory=list)


@dataclass
class HidatoPuzzle:
    grid: HexGrid
    cells: Dict[str, Cell]
    coord_to_id: Dict[Coord, str]
    id_to_coord: Dict[str, Coord]
    total_numbers: int
    fixed_values: Dict[int, str]   # value -> cell_id for given clues


@dataclass
class SolverMetrics:
    runtime_seconds: float = 0.0
    nodes_expanded: int = 0
    backtracks: int = 0


@dataclass
class SolverResult:
    success: bool
    solved_grid: Optional[HexGrid]
    metrics: SolverMetrics
    message: str


# -----------------------------
# Utility functions
# -----------------------------

def clone_grid(grid: HexGrid) -> HexGrid:
    return [row[:] for row in grid]


def get_expected_range(grid: HexGrid) -> int:
    return sum(len(row) for row in grid)


def get_given_mask(grid: HexGrid) -> List[List[bool]]:
    return [[cell is not None for cell in row] for row in grid]


def get_adjacent_coords(grid: HexGrid, r: int, c: int) -> List[Coord]:
    """
    Hex-neighbor logic matching the board shape used in the frontend.
    """
    neighbors: List[Coord] = []
    current_len = len(grid[r])

    # left / right
    if c - 1 >= 0:
        neighbors.append((r, c - 1))
    if c + 1 < current_len:
        neighbors.append((r, c + 1))

    # upper row
    if r - 1 >= 0:
        upper_len = len(grid[r - 1])

        if upper_len == current_len - 1:
            if 0 <= c - 1 < upper_len:
                neighbors.append((r - 1, c - 1))
            if 0 <= c < upper_len:
                neighbors.append((r - 1, c))
        elif upper_len == current_len + 1:
            if 0 <= c < upper_len:
                neighbors.append((r - 1, c))
            if 0 <= c + 1 < upper_len:
                neighbors.append((r - 1, c + 1))
        else:
            if 0 <= c < upper_len:
                neighbors.append((r - 1, c))
            if 0 <= c - 1 < upper_len:
                neighbors.append((r - 1, c - 1))

    # lower row
    if r + 1 < len(grid):
        lower_len = len(grid[r + 1])

        if lower_len == current_len - 1:
            if 0 <= c - 1 < lower_len:
                neighbors.append((r + 1, c - 1))
            if 0 <= c < lower_len:
                neighbors.append((r + 1, c))
        elif lower_len == current_len + 1:
            if 0 <= c < lower_len:
                neighbors.append((r + 1, c))
            if 0 <= c + 1 < lower_len:
                neighbors.append((r + 1, c + 1))
        else:
            if 0 <= c < lower_len:
                neighbors.append((r + 1, c))
            if 0 <= c - 1 < lower_len:
                neighbors.append((r + 1, c - 1))

    # deduplicate while preserving order
    unique: List[Coord] = []
    seen = set()
    for coord in neighbors:
        if coord not in seen:
            seen.add(coord)
            unique.append(coord)

    return unique


def build_puzzle(grid: HexGrid) -> HidatoPuzzle:
    """
    Convert the raw grid into a frozen internal model:
    - each cell has an id
    - current value
    - fixed flag
    - neighbor cell ids
    """
    cells: Dict[str, Cell] = {}
    coord_to_id: Dict[Coord, str] = {}
    id_to_coord: Dict[str, Coord] = {}
    fixed_values: Dict[int, str] = {}

    for r, row in enumerate(grid):
        for c, value in enumerate(row):
            cell_id = f"r{r}c{c}"
            fixed = value is not None

            cell = Cell(
                cell_id=cell_id,
                row=r,
                col=c,
                value=value,
                fixed=fixed,
                neighbors=[]
            )

            cells[cell_id] = cell
            coord_to_id[(r, c)] = cell_id
            id_to_coord[cell_id] = (r, c)

            if value is not None:
                if value in fixed_values:
                    raise ValueError(f"Duplicate fixed clue found: {value}")
                fixed_values[value] = cell_id

    for (r, c), cell_id in coord_to_id.items():
        neighbor_coords = get_adjacent_coords(grid, r, c)
        cells[cell_id].neighbors = [coord_to_id[(nr, nc)] for nr, nc in neighbor_coords]

    total_numbers = get_expected_range(grid)

    return HidatoPuzzle(
        grid=clone_grid(grid),
        cells=cells,
        coord_to_id=coord_to_id,
        id_to_coord=id_to_coord,
        total_numbers=total_numbers,
        fixed_values=fixed_values
    )


def grid_from_assignment(puzzle: HidatoPuzzle, assignment: Dict[str, int]) -> HexGrid:
    """
    Convert a solved assignment {cell_id -> value} back to grid format.
    """
    output: HexGrid = []
    for r, row in enumerate(puzzle.grid):
        new_row: List[Optional[int]] = []
        for c, _ in enumerate(row):
            cell_id = puzzle.coord_to_id[(r, c)]
            new_row.append(assignment[cell_id])
        output.append(new_row)
    return output


# -----------------------------
# Solver
# -----------------------------

class HidatoBacktrackingSolver:
    """
    Baseline backtracking solver.

    State we maintain:
    - assignment: cell_id -> value
    - value_to_cell: value -> cell_id
    - used_values: set of values already placed

    Strategy:
    - place numbers from 1..N
    - if k-1 is known, try placing k near k-1
    - if k+1 is fixed/known, also require adjacency to k+1
    - do not overwrite fixed clues
    - collect metrics
    """

    def __init__(self, puzzle: HidatoPuzzle):
        self.puzzle = puzzle
        self.N = puzzle.total_numbers

        self.metrics = SolverMetrics()

        # Initial assignment from givens
        self.assignment: Dict[str, int] = {}
        self.value_to_cell: Dict[int, str] = {}
        self.used_values: Set[int] = set()

        for cell_id, cell in puzzle.cells.items():
            if cell.value is not None:
                value = cell.value

                if not (1 <= value <= self.N):
                    raise ValueError(f"Value {value} is out of range 1..{self.N}")

                if value in self.used_values:
                    raise ValueError(f"Duplicate value found in puzzle: {value}")

                self.assignment[cell_id] = value
                self.value_to_cell[value] = cell_id
                self.used_values.add(value)

    def solve(self) -> SolverResult:
        start = time.perf_counter()

        valid, message = self._validate_initial_clues()
        if not valid:
            self.metrics.runtime_seconds = time.perf_counter() - start
            return SolverResult(
                success=False,
                solved_grid=None,
                metrics=self.metrics,
                message=message
            )

        success = self._backtrack()

        self.metrics.runtime_seconds = time.perf_counter() - start

        if success:
            solved_grid = grid_from_assignment(self.puzzle, self.assignment)
            return SolverResult(
                success=True,
                solved_grid=solved_grid,
                metrics=self.metrics,
                message="Puzzle solved successfully."
            )

        return SolverResult(
            success=False,
            solved_grid=None,
            metrics=self.metrics,
            message="No solution found."
        )

    def _validate_initial_clues(self) -> Tuple[bool, str]:
        """
        Check whether fixed clues already violate adjacency.
        If both k and k+1 are already given, they must be adjacent.
        """
        for k in range(1, self.N):
            if k in self.value_to_cell and (k + 1) in self.value_to_cell:
                a = self.value_to_cell[k]
                b = self.value_to_cell[k + 1]
                if b not in self.puzzle.cells[a].neighbors:
                    return False, f"Invalid puzzle: fixed clues {k} and {k + 1} are not adjacent."
        return True, "Initial clues are valid."

    def _backtrack(self) -> bool:
        if len(self.value_to_cell) == self.N:
            return True

        self.metrics.nodes_expanded += 1

        k = self._choose_next_value()
        candidates = self._candidate_cells_for_value(k)

        for cell_id in candidates:
            if self._can_place(k, cell_id):
                self._place(k, cell_id)

                if self._backtrack():
                    return True

                self._remove(k, cell_id)
                self.metrics.backtracks += 1

        return False

    def _choose_next_value(self) -> int:
        """
        Baseline choice:
        return the smallest value not yet placed.
        """
        for k in range(1, self.N + 1):
            if k not in self.value_to_cell:
                return k
        raise RuntimeError("No unplaced value found, but solver is not finished.")

    def _candidate_cells_for_value(self, k: int) -> List[str]:
        """
        Candidate generation:
        - if k is fixed, only that one cell
        - if k-1 is already placed, candidates = unassigned neighbors of k-1
        - otherwise fallback = any unassigned cell

        This is still backtracking, just with pruning.
        """
        if k in self.puzzle.fixed_values:
            return [self.puzzle.fixed_values[k]]

        if (k - 1) in self.value_to_cell:
            prev_cell = self.value_to_cell[k - 1]
            candidate_ids: List[str] = []
            for nbr in self.puzzle.cells[prev_cell].neighbors:
                if nbr not in self.assignment:
                    candidate_ids.append(nbr)
            return candidate_ids

        return [cell_id for cell_id in self.puzzle.cells if cell_id not in self.assignment]

    def _can_place(self, k: int, cell_id: str) -> bool:
        cell = self.puzzle.cells[cell_id]

        if cell_id in self.assignment:
            return False

        if k in self.used_values:
            return False

        if cell.fixed and cell.value != k:
            return False

        if k in self.puzzle.fixed_values and self.puzzle.fixed_values[k] != cell_id:
            return False

        if (k - 1) in self.value_to_cell:
            prev_cell = self.value_to_cell[k - 1]
            if cell_id not in self.puzzle.cells[prev_cell].neighbors:
                return False

        if (k + 1) in self.value_to_cell:
            next_cell = self.value_to_cell[k + 1]
            if cell_id not in self.puzzle.cells[next_cell].neighbors:
                return False

        if (k + 1) in self.puzzle.fixed_values and (k + 1) not in self.value_to_cell:
            fixed_next = self.puzzle.fixed_values[k + 1]
            if fixed_next not in self.puzzle.cells[cell_id].neighbors:
                return False

        if (k - 1) in self.puzzle.fixed_values and (k - 1) not in self.value_to_cell:
            fixed_prev = self.puzzle.fixed_values[k - 1]
            if fixed_prev not in self.puzzle.cells[cell_id].neighbors:
                return False

        return True

    def _place(self, k: int, cell_id: str) -> None:
        self.assignment[cell_id] = k
        self.value_to_cell[k] = cell_id
        self.used_values.add(k)

    def _remove(self, k: int, cell_id: str) -> None:
        del self.assignment[cell_id]
        del self.value_to_cell[k]
        self.used_values.remove(k)


# -----------------------------
# Public helper for API/server
# -----------------------------

def solve_hidato_grid(grid: HexGrid) -> SolverResult:
    """
    Helper function for backend API usage.
    """
    puzzle = build_puzzle(grid)
    solver = HidatoBacktrackingSolver(puzzle)
    return solver.solve()


# -----------------------------
# Pretty printing / validation
# -----------------------------

def print_grid(grid: HexGrid) -> None:
    for row in grid:
        print(" ".join("." if v is None else f"{v:2d}" for v in row))


def validate_solution(grid: HexGrid) -> Tuple[bool, str]:
    """
    Full validation for a completed solution.
    """
    N = get_expected_range(grid)
    positions: Dict[int, Coord] = {}

    for r, row in enumerate(grid):
        for c, value in enumerate(row):
            if value is None:
                return False, "Grid still has empty cells."
            if not (1 <= value <= N):
                return False, f"Value {value} out of range 1..{N}."
            if value in positions:
                return False, f"Duplicate value {value}."
            positions[value] = (r, c)

    for k in range(1, N):
        a = positions[k]
        b = positions[k + 1]
        if b not in get_adjacent_coords(grid, a[0], a[1]):
            return False, f"{k} and {k + 1} are not adjacent."

    return True, "Valid Hidato solution."


# -----------------------------
# Example puzzles
# -----------------------------

PUZZLES: Dict[str, HexGrid] = {
    "Easy": [
        [1, None, 3],
        [12, None, None, 4],
        [None, None, None, 15, 5],
        [10, None, 16, None],
        [None, 8, 7],
    ],
    "Medium": [
        [None, None, 4, None],
        [1, None, None, None, 8],
        [None, 11, None, None, None, None],
        [None, None, 15, None, 18],
        [None, None, None, None],
    ],
    "Hard": [
        [None, None, None, None, None],
        [None, 8, None, None, None, 14],
        [1, None, None, 18, None, None, None],
        [None, None, 22, None, None, 26, None, None],
        [None, 30, None, None, 33, None, None],
        [None, None, None, 37, None, 40],
        [None, 43, None, None, None],
    ],
}


# -----------------------------
# Example run
# -----------------------------

if __name__ == "__main__":
    puzzle_name = "Easy"
    raw_grid = PUZZLES[puzzle_name]

    print(f"\n--- {puzzle_name} puzzle ---")
    print_grid(raw_grid)

    result = solve_hidato_grid(raw_grid)

    print("\n--- Solver result ---")
    print("Success:", result.success)
    print("Message:", result.message)
    print(f"Runtime: {result.metrics.runtime_seconds:.6f} sec")
    print("Nodes expanded:", result.metrics.nodes_expanded)
    print("Backtracks:", result.metrics.backtracks)

    if result.solved_grid is not None:
        print("\n--- Solved grid ---")
        print_grid(result.solved_grid)

        ok, msg = validate_solution(result.solved_grid)
        print("\nValidation:", ok, "-", msg)