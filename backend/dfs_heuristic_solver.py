from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import time

from hidato_backtracking import (
    Coord,
    HexGrid,
    Cell,
    HidatoPuzzle,
    SolverMetrics,
    SolverResult,
    build_puzzle,
    grid_from_assignment,
)


CellId = str


class HidatoDFSHeuristicSolver:
    """
    DFS + heuristic ordering solver.

    Differences from baseline DFS:
    - same correctness / completeness
    - same backtracking structure
    - candidate cells are ordered using a heuristic:
        * closer to future fixed clues
        * more onward flexibility
        * preserve future reachability
    """

    def __init__(self, puzzle: HidatoPuzzle):
        self.puzzle = puzzle
        self.N = puzzle.total_numbers
        self.metrics = SolverMetrics()

        self.assignment: Dict[CellId, int] = {}
        self.value_to_cell: Dict[int, CellId] = {}
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

        self.distances = self._compute_all_pairs_shortest_paths()

    # -----------------------------
    # Public solve
    # -----------------------------

    def solve(self) -> SolverResult:
        start = time.perf_counter()

        valid, message = self._validate_initial_clues()
        if not valid:
            self.metrics.runtime_seconds = time.perf_counter() - start
            return SolverResult(
                success=False,
                solved_grid=None,
                metrics=self.metrics,
                message=message,
            )

        success = self._backtrack()

        self.metrics.runtime_seconds = time.perf_counter() - start

        if success:
            solved_grid = grid_from_assignment(self.puzzle, self.assignment)
            return SolverResult(
                success=True,
                solved_grid=solved_grid,
                metrics=self.metrics,
                message="Puzzle solved successfully with DFS + heuristics.",
            )

        return SolverResult(
            success=False,
            solved_grid=None,
            metrics=self.metrics,
            message="No solution found.",
        )

    # -----------------------------
    # Core DFS
    # -----------------------------

    def _backtrack(self) -> bool:
        if len(self.value_to_cell) == self.N:
            return True

        self.metrics.nodes_expanded += 1

        k = self._choose_next_value()
        candidates = self._candidate_cells_for_value(k)
        ordered_candidates = self._order_candidates(k, candidates)

        for cell_id in ordered_candidates:
            if self._can_place(k, cell_id):
                self._place(k, cell_id)

                if self._backtrack():
                    return True

                self._remove(k, cell_id)
                self.metrics.backtracks += 1

        return False

    def _choose_next_value(self) -> int:
        """
        Still place values in ascending order.
        This keeps comparison with baseline DFS clean.
        """
        for k in range(1, self.N + 1):
            if k not in self.value_to_cell:
                return k
        raise RuntimeError("No unplaced value found, but solver not finished.")

    # -----------------------------
    # Candidate generation
    # -----------------------------

    def _candidate_cells_for_value(self, k: int) -> List[CellId]:
        if k in self.puzzle.fixed_values:
            return [self.puzzle.fixed_values[k]]

        if (k - 1) in self.value_to_cell:
            prev_cell = self.value_to_cell[k - 1]
            return [
                nbr for nbr in self.puzzle.cells[prev_cell].neighbors
                if nbr not in self.assignment
            ]

        return [cell_id for cell_id in self.puzzle.cells if cell_id not in self.assignment]

    def _order_candidates(self, k: int, candidates: List[CellId]) -> List[CellId]:
        """
        Heuristic ordering:
        lower score is better

        Components:
        1. future fixed clue distance (strong)
        2. onward flexibility for k+1 (prefer more options)
        3. total future slack (prefer tighter but still feasible)
        """
        scored: List[Tuple[Tuple[int, int, int], CellId]] = []

        for cell_id in candidates:
            score = self._candidate_score(k, cell_id)
            if score is not None:
                scored.append((score, cell_id))

        scored.sort(key=lambda x: x[0])
        return [cell_id for _, cell_id in scored]

    def _candidate_score(self, k: int, cell_id: CellId) -> Optional[Tuple[int, int, int]]:
        """
        Return a tuple score:
        (distance_to_next_fixed, -onward_options, total_slack)

        Lower is better.
        Return None if the candidate should be pruned immediately.
        """
        # Must remain feasible for future fixed clues
        future_score = self._future_fixed_score(k, cell_id)
        if future_score is None:
            return None

        distance_to_next_fixed, total_slack = future_score

        onward_options = self._count_onward_options(k, cell_id)

        # lower better:
        # - closer to next fixed clue
        # - more onward options (so use negative)
        # - lower slack means more directed
        return (distance_to_next_fixed, -onward_options, total_slack)

    def _future_fixed_score(self, k: int, cell_id: CellId) -> Optional[Tuple[int, int]]:
        """
        Check future fixed clues and compute:
        - distance to nearest future fixed clue in value order
        - total slack across all future fixed clues

        If any future fixed clue becomes unreachable, return None.
        """
        next_fixed_distance: Optional[int] = None
        total_slack = 0

        for future_value in range(k + 1, self.N + 1):
            if future_value not in self.puzzle.fixed_values:
                continue

            future_cell = self.puzzle.fixed_values[future_value]
            available_steps = future_value - k
            dist = self.distances[cell_id][future_cell]

            if dist > available_steps:
                return None

            slack = available_steps - dist
            total_slack += slack

            if next_fixed_distance is None:
                next_fixed_distance = dist

        if next_fixed_distance is None:
            next_fixed_distance = 0

        return (next_fixed_distance, total_slack)

    def _count_onward_options(self, k: int, cell_id: CellId) -> int:
        """
        Estimate how flexible the next step will be after placing k at cell_id.
        """
        next_value = k + 1
        if next_value > self.N:
            return 0

        if next_value in self.puzzle.fixed_values:
            fixed_next = self.puzzle.fixed_values[next_value]
            return 1 if fixed_next in self.puzzle.cells[cell_id].neighbors else 0

        count = 0
        for nbr in self.puzzle.cells[cell_id].neighbors:
            if nbr in self.assignment:
                continue
            # mild feasibility check for k+1
            feasible = True
            for future_value in range(next_value + 1, self.N + 1):
                if future_value not in self.puzzle.fixed_values:
                    continue
                future_cell = self.puzzle.fixed_values[future_value]
                available_steps = future_value - next_value
                dist = self.distances[nbr][future_cell]
                if dist > available_steps:
                    feasible = False
                    break
            if feasible:
                count += 1
        return count

    # -----------------------------
    # Placement checks
    # -----------------------------

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

        # stronger future reachability pruning
        for future_value, future_cell in self.puzzle.fixed_values.items():
            if future_value <= k:
                continue
            available_steps = future_value - k
            dist = self.distances[cell_id][future_cell]
            if dist > available_steps:
                return False

        return True

    # -----------------------------
    # State update
    # -----------------------------

    def _place(self, k: int, cell_id: str) -> None:
        self.assignment[cell_id] = k
        self.value_to_cell[k] = cell_id
        self.used_values.add(k)

    def _remove(self, k: int, cell_id: str) -> None:
        del self.assignment[cell_id]
        del self.value_to_cell[k]
        self.used_values.remove(k)

    # -----------------------------
    # Validation / graph distances
    # -----------------------------

    def _validate_initial_clues(self) -> Tuple[bool, str]:
        for k in range(1, self.N):
            if k in self.value_to_cell and (k + 1) in self.value_to_cell:
                a = self.value_to_cell[k]
                b = self.value_to_cell[k + 1]
                if b not in self.puzzle.cells[a].neighbors:
                    return False, f"Invalid puzzle: fixed clues {k} and {k+1} are not adjacent."
        return True, "Initial clues are valid."

    def _compute_all_pairs_shortest_paths(self) -> Dict[CellId, Dict[CellId, int]]:
        distances: Dict[CellId, Dict[CellId, int]] = {}
        for start_cell in self.puzzle.cells.keys():
            distances[start_cell] = self._bfs_distances(start_cell)
        return distances

    def _bfs_distances(self, start_cell: CellId) -> Dict[CellId, int]:
        queue: List[CellId] = [start_cell]
        dist: Dict[CellId, int] = {start_cell: 0}
        idx = 0

        while idx < len(queue):
            current = queue[idx]
            idx += 1

            for nbr in self.puzzle.cells[current].neighbors:
                if nbr not in dist:
                    dist[nbr] = dist[current] + 1
                    queue.append(nbr)

        return dist


def solve_hidato_dfs_heuristic_grid(grid: HexGrid) -> SolverResult:
    puzzle = build_puzzle(grid)
    solver = HidatoDFSHeuristicSolver(puzzle)
    return solver.solve()


if __name__ == "__main__":
    test_grid: HexGrid = [
        [1, None, 3],
        [12, None, None, 4],
        [None, None, None, 15, 5],
        [10, None, 16, None],
        [None, 8, 7],
    ]

    result = solve_hidato_dfs_heuristic_grid(test_grid)

    print("Success:", result.success)
    print("Message:", result.message)
    print(f"Runtime: {result.metrics.runtime_seconds:.6f} sec")
    print("Nodes expanded:", result.metrics.nodes_expanded)
    print("Backtracks:", result.metrics.backtracks)

    if result.solved_grid:
        for row in result.solved_grid:
            print(row)