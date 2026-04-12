from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Set, Tuple
import heapq
import itertools
import time

from hidato_backtracking import (
    HexGrid,
    HidatoPuzzle,
    SolverMetrics,
    SolverResult,
    build_puzzle,
    grid_from_assignment,
)


CellId = str


@dataclass(order=True)
class AStarState:
    priority: int
    tie_break: int
    next_value: int = field(compare=False)
    assignment: Dict[CellId, int] = field(compare=False)
    value_to_cell: Dict[int, CellId] = field(compare=False)
    used_cells: FrozenSet[CellId] = field(compare=False)
    g_cost: int = field(compare=False)
    current_cell: Optional[CellId] = field(compare=False, default=None)


class HidatoAStarSolver:
    def __init__(self, puzzle: HidatoPuzzle):
        self.puzzle = puzzle
        self.N = puzzle.total_numbers
        self.metrics = SolverMetrics()
        self._counter = itertools.count()

        self.initial_assignment: Dict[CellId, int] = {}
        self.initial_value_to_cell: Dict[int, CellId] = {}
        self.initial_used_cells: Set[CellId] = set()

        for cell_id, cell in puzzle.cells.items():
            if cell.value is not None:
                value = cell.value
                self.initial_assignment[cell_id] = value
                self.initial_value_to_cell[value] = cell_id
                self.initial_used_cells.add(cell_id)

        self.distances = self._compute_all_pairs_shortest_paths()

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

        try:
            frontier: List[AStarState] = []
            visited_best_g: Dict[Tuple[int, FrozenSet[Tuple[CellId, int]]], int] = {}

            start_states = self._build_start_states()

            for state in start_states:
                heapq.heappush(frontier, state)

            while frontier:
                state = heapq.heappop(frontier)
                self.metrics.nodes_expanded += 1

                if state.next_value > self.N:
                    solved_grid = grid_from_assignment(self.puzzle, state.assignment)
                    self.metrics.runtime_seconds = time.perf_counter() - start
                    return SolverResult(
                        success=True,
                        solved_grid=solved_grid,
                        metrics=self.metrics,
                        message="Puzzle solved successfully with A*.",
                    )

                state_key = (
                    state.next_value,
                    frozenset(state.assignment.items()),
                )

                best_g = visited_best_g.get(state_key)
                if best_g is not None and best_g <= state.g_cost:
                    continue
                visited_best_g[state_key] = state.g_cost

                candidates = self._candidate_cells_for_value(state, state.next_value)

                for cell_id in candidates:
                    if not self._can_place(state, state.next_value, cell_id):
                        continue

                    new_assignment = dict(state.assignment)
                    new_value_to_cell = dict(state.value_to_cell)
                    new_used = set(state.used_cells)

                    new_assignment[cell_id] = state.next_value
                    new_value_to_cell[state.next_value] = cell_id
                    new_used.add(cell_id)

                    next_value = self._next_unassigned_value(
                        state.next_value + 1,
                        new_value_to_cell,
                    )
                    g_cost = state.g_cost + 1

                    heuristic = self._heuristic(next_value, cell_id, new_value_to_cell)
                    if heuristic is None:
                        continue

                    new_state = AStarState(
                        priority=g_cost + heuristic,
                        tie_break=next(self._counter),
                        next_value=next_value,
                        assignment=new_assignment,
                        value_to_cell=new_value_to_cell,
                        used_cells=frozenset(new_used),
                        g_cost=g_cost,
                        current_cell=cell_id,
                    )

                    heapq.heappush(frontier, new_state)

            self.metrics.runtime_seconds = time.perf_counter() - start
            return SolverResult(
                success=False,
                solved_grid=None,
                metrics=self.metrics,
                message="No solution found.",
            )

        except Exception as e:
            self.metrics.runtime_seconds = time.perf_counter() - start
            return SolverResult(
                success=False,
                solved_grid=None,
                metrics=self.metrics,
                message=f"A* solver error: {str(e)}",
            )

    def _build_start_states(self) -> List[AStarState]:
        states: List[AStarState] = []

        if 1 in self.initial_value_to_cell:
            cell_id = self.initial_value_to_cell[1]
            next_value = self._next_unassigned_value(2, self.initial_value_to_cell)
            heuristic = self._heuristic(next_value, cell_id, self.initial_value_to_cell)
            if heuristic is not None:
                states.append(
                    AStarState(
                        priority=1 + heuristic,
                        tie_break=next(self._counter),
                        next_value=next_value,
                        assignment=dict(self.initial_assignment),
                        value_to_cell=dict(self.initial_value_to_cell),
                        used_cells=frozenset(self.initial_used_cells),
                        g_cost=1,
                        current_cell=cell_id,
                    )
                )
            return states

        for cell_id in self.puzzle.cells.keys():
            if cell_id in self.initial_assignment:
                continue

            assignment = dict(self.initial_assignment)
            value_to_cell = dict(self.initial_value_to_cell)
            used = set(self.initial_used_cells)

            assignment[cell_id] = 1
            value_to_cell[1] = cell_id
            used.add(cell_id)

            next_value = self._next_unassigned_value(2, value_to_cell)
            heuristic = self._heuristic(next_value, cell_id, value_to_cell)
            if heuristic is None:
                continue

            states.append(
                AStarState(
                    priority=1 + heuristic,
                    tie_break=next(self._counter),
                    next_value=next_value,
                    assignment=assignment,
                    value_to_cell=value_to_cell,
                    used_cells=frozenset(used),
                    g_cost=1,
                    current_cell=cell_id,
                )
            )

        return states

    def _next_unassigned_value(
        self,
        start_value: int,
        value_to_cell: Dict[int, CellId],
    ) -> int:
        k = start_value
        while k <= self.N and k in value_to_cell:
            k += 1
        return k

    def _candidate_cells_for_value(self, state: AStarState, k: int) -> List[CellId]:
        if k in state.value_to_cell:
            return [state.value_to_cell[k]]

        if k in self.puzzle.fixed_values:
            return [self.puzzle.fixed_values[k]]

        if (k - 1) in state.value_to_cell:
            prev_cell = state.value_to_cell[k - 1]
            return [
                nbr for nbr in self.puzzle.cells[prev_cell].neighbors
                if nbr not in state.used_cells
            ]

        return [cell_id for cell_id in self.puzzle.cells if cell_id not in state.used_cells]

    def _can_place(self, state: AStarState, k: int, cell_id: CellId) -> bool:
        cell = self.puzzle.cells[cell_id]

        if k in state.value_to_cell:
            return state.value_to_cell[k] == cell_id

        if cell_id in state.used_cells:
            return False

        if cell.fixed and cell.value != k:
            return False

        if k in self.puzzle.fixed_values and self.puzzle.fixed_values[k] != cell_id:
            return False

        if (k - 1) in state.value_to_cell:
            prev_cell = state.value_to_cell[k - 1]
            if cell_id not in self.puzzle.cells[prev_cell].neighbors:
                return False

        if (k + 1) in state.value_to_cell:
            next_cell = state.value_to_cell[k + 1]
            if cell_id not in self.puzzle.cells[next_cell].neighbors:
                return False

        if (k + 1) in self.puzzle.fixed_values and (k + 1) not in state.value_to_cell:
            fixed_next = self.puzzle.fixed_values[k + 1]
            if fixed_next not in self.puzzle.cells[cell_id].neighbors:
                return False

        for future_value, future_cell in self.puzzle.fixed_values.items():
            if future_value <= k:
                continue
            steps_available = future_value - k
            dist = self.distances[cell_id][future_cell]
            if dist > steps_available:
                return False

        return True

    def _heuristic(
        self,
        next_value: int,
        current_cell: CellId,
        value_to_cell: Dict[int, CellId],
    ) -> Optional[int]:
        if next_value > self.N:
            return 0

        current_value = next_value - 1
        total_slack = 0

        for future_value, future_cell in self.puzzle.fixed_values.items():
            if future_value <= current_value:
                continue

            available_steps = future_value - current_value
            dist = self.distances[current_cell][future_cell]

            if dist > available_steps:
                return None

            total_slack += (available_steps - dist)

        return total_slack

    def _validate_initial_clues(self) -> Tuple[bool, str]:
        for k in range(1, self.N):
            if k in self.initial_value_to_cell and (k + 1) in self.initial_value_to_cell:
                a = self.initial_value_to_cell[k]
                b = self.initial_value_to_cell[k + 1]
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


def solve_hidato_astar_grid(grid: HexGrid) -> SolverResult:
    puzzle = build_puzzle(grid)
    solver = HidatoAStarSolver(puzzle)
    return solver.solve()


if __name__ == "__main__":
    test_grid: HexGrid = [
        [1, None, 3],
        [12, None, None, 4],
        [None, None, None, 15, 5],
        [10, None, 16, None],
        [None, 8, 7],
    ]

    result = solve_hidato_astar_grid(test_grid)

    print("Success:", result.success)
    print("Message:", result.message)
    print(f"Runtime: {result.metrics.runtime_seconds:.6f} sec")
    print("Nodes expanded:", result.metrics.nodes_expanded)
    print("Backtracks:", result.metrics.backtracks)

    if result.solved_grid:
        for row in result.solved_grid:
            print(row)