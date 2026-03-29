from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
import time

from hidato_backtracking import (
    Cell,
    Coord,
    HexGrid,
    HidatoPuzzle,
    SolverMetrics,
    SolverResult,
    build_puzzle,
    grid_from_assignment,
)


DomainMap = Dict[int, Set[str]]  # value -> possible cell_ids


@dataclass
class CSPState:
    domains: DomainMap
    assignment: Dict[int, str]   # value -> cell_id


class HidatoCSPSolver:
    """
    CSP solver for Hidato using:
    - variables = values 1..N
    - domains = candidate cells for each value
    - propagation:
        * all-different on cells
        * adjacency restriction for consecutive values
        * singleton propagation
    """

    def __init__(self, puzzle: HidatoPuzzle):
        self.puzzle = puzzle
        self.N = puzzle.total_numbers
        self.metrics = SolverMetrics()

        self.all_cell_ids = set(puzzle.cells.keys())

        self.initial_domains = self._build_initial_domains()

    def solve(self) -> SolverResult:
        start = time.perf_counter()

        try:
            state = CSPState(
                domains={k: set(v) for k, v in self.initial_domains.items()},
                assignment={}
            )

            ok = self._propagate(state)
            if not ok:
                self.metrics.runtime_seconds = time.perf_counter() - start
                return SolverResult(
                    success=False,
                    solved_grid=None,
                    metrics=self.metrics,
                    message="No solution found during initial CSP propagation."
                )

            success, final_assignment = self._search(state)

            self.metrics.runtime_seconds = time.perf_counter() - start

            if success and final_assignment is not None:
                cell_assignment = {cell_id: value for value, cell_id in final_assignment.items()}
                solved_grid = grid_from_assignment(self.puzzle, cell_assignment)

                return SolverResult(
                    success=True,
                    solved_grid=solved_grid,
                    metrics=self.metrics,
                    message="Puzzle solved successfully with CSP propagation."
                )

            return SolverResult(
                success=False,
                solved_grid=None,
                metrics=self.metrics,
                message="No solution found."
            )

        except Exception as e:
            self.metrics.runtime_seconds = time.perf_counter() - start
            return SolverResult(
                success=False,
                solved_grid=None,
                metrics=self.metrics,
                message=f"CSP solver error: {str(e)}"
            )

    # ---------------------------------
    # Initial domains
    # ---------------------------------

    def _build_initial_domains(self) -> DomainMap:
        """
        Build initial candidate cells for each value 1..N.
        Fixed clues become singleton domains.
        Non-fixed values can go to any non-conflicting cell initially.
        """
        domains: DomainMap = {}

        for k in range(1, self.N + 1):
            if k in self.puzzle.fixed_values:
                domains[k] = {self.puzzle.fixed_values[k]}
            else:
                candidate_cells: Set[str] = set()

                for cell_id, cell in self.puzzle.cells.items():
                    if cell.fixed:
                        # fixed cells can only take their fixed value
                        continue
                    candidate_cells.add(cell_id)

                domains[k] = candidate_cells

        # Early adjacency filtering from fixed clues
        for k in range(1, self.N + 1):
            if k - 1 in domains and len(domains[k - 1]) == 1:
                prev_cell = next(iter(domains[k - 1]))
                if k not in self.puzzle.fixed_values:
                    domains[k] &= set(self.puzzle.cells[prev_cell].neighbors) | domains[k]

            if k + 1 in domains and len(domains[k + 1]) == 1:
                next_cell = next(iter(domains[k + 1]))
                if k not in self.puzzle.fixed_values:
                    domains[k] &= set(self.puzzle.cells[next_cell].neighbors) | domains[k]

        # Also enforce fixed clue adjacency consistency
        for k in range(1, self.N):
            if k in self.puzzle.fixed_values and (k + 1) in self.puzzle.fixed_values:
                a = self.puzzle.fixed_values[k]
                b = self.puzzle.fixed_values[k + 1]
                if b not in self.puzzle.cells[a].neighbors:
                    raise ValueError(f"Invalid puzzle: fixed clues {k} and {k+1} are not adjacent.")

        return domains

    # ---------------------------------
    # Propagation
    # ---------------------------------

    def _propagate(self, state: CSPState) -> bool:
        """
        Repeatedly apply:
        1. If domain size = 1, assign it
        2. Remove assigned cells from other domains
        3. Restrict neighbors for consecutive values
        """
        changed = True

        while changed:
            changed = False

            # Fail if any domain is empty
            for k in range(1, self.N + 1):
                if len(state.domains[k]) == 0:
                    return False

            # Singleton domains -> assignment
            for k in range(1, self.N + 1):
                if len(state.domains[k]) == 1 and k not in state.assignment:
                    state.assignment[k] = next(iter(state.domains[k]))
                    changed = True

            # All-different propagation:
            # assigned cell cannot appear in any other domain
            assigned_items = list(state.assignment.items())
            for k, assigned_cell in assigned_items:
                for other in range(1, self.N + 1):
                    if other == k:
                        continue
                    if assigned_cell in state.domains[other]:
                        before = len(state.domains[other])
                        state.domains[other].discard(assigned_cell)
                        if len(state.domains[other]) != before:
                            changed = True
                            if len(state.domains[other]) == 0:
                                return False

            # Consecutive adjacency propagation
            for k in range(1, self.N + 1):
                # If k assigned, k-1 and k+1 must be neighbors of k's cell
                if k in state.assignment:
                    cell_id = state.assignment[k]
                    neighbor_cells = set(self.puzzle.cells[cell_id].neighbors)

                    if k - 1 >= 1:
                        before = len(state.domains[k - 1])
                        state.domains[k - 1] &= neighbor_cells if (k - 1) not in self.puzzle.fixed_values else state.domains[k - 1]
                        if len(state.domains[k - 1]) != before:
                            changed = True
                            if len(state.domains[k - 1]) == 0:
                                return False

                    if k + 1 <= self.N:
                        before = len(state.domains[k + 1])
                        state.domains[k + 1] &= neighbor_cells if (k + 1) not in self.puzzle.fixed_values else state.domains[k + 1]
                        if len(state.domains[k + 1]) != before:
                            changed = True
                            if len(state.domains[k + 1]) == 0:
                                return False

                # If both k and k+1 are not assigned but one has a domain,
                # enforce arc-like consistency:
                # a cell in domain[k] is allowed only if it has at least one neighboring
                # cell in domain[k+1], and vice versa.
                if k < self.N:
                    if not self._revise_pair(state, k, k + 1):
                        return False
                    if not self._revise_pair(state, k + 1, k):
                        return False

        return True

    def _revise_pair(self, state: CSPState, a: int, b: int) -> bool:
        """
        Domain[a] should keep only cells that have at least one neighboring cell in Domain[b].
        """
        allowed_b = state.domains[b]
        new_domain_a: Set[str] = set()

        for cell_a in state.domains[a]:
            neighbors_a = set(self.puzzle.cells[cell_a].neighbors)
            if neighbors_a & allowed_b:
                new_domain_a.add(cell_a)

        if len(new_domain_a) == 0:
            return False

        state.domains[a] = new_domain_a
        return True

    # ---------------------------------
    # Search
    # ---------------------------------

    def _search(self, state: CSPState) -> Tuple[bool, Optional[Dict[int, str]]]:
        if len(state.assignment) == self.N:
            return True, dict(state.assignment)

        self.metrics.nodes_expanded += 1

        value = self._select_unassigned_variable(state)
        candidates = sorted(state.domains[value])

        for cell_id in candidates:
            new_state = CSPState(
                domains={k: set(v) for k, v in state.domains.items()},
                assignment=dict(state.assignment),
            )

            new_state.domains[value] = {cell_id}
            new_state.assignment[value] = cell_id

            if self._propagate(new_state):
                success, final_assignment = self._search(new_state)
                if success:
                    return True, final_assignment

            self.metrics.backtracks += 1

        return False, None

    def _select_unassigned_variable(self, state: CSPState) -> int:
        """
        MRV heuristic: choose the unassigned value with smallest domain.
        """
        unassigned = [k for k in range(1, self.N + 1) if k not in state.assignment]
        return min(unassigned, key=lambda k: len(state.domains[k]))


# ---------------------------------
# Public helper
# ---------------------------------

def solve_hidato_csp_grid(grid: HexGrid) -> SolverResult:
    puzzle = build_puzzle(grid)
    solver = HidatoCSPSolver(puzzle)
    return solver.solve()


# ---------------------------------
# Example run
# ---------------------------------

if __name__ == "__main__":
    test_grid: HexGrid = [
        [1, None, 3],
        [12, None, None, 4],
        [None, None, None, 15, 5],
        [10, None, 16, None],
        [None, 8, 7],
    ]

    result = solve_hidato_csp_grid(test_grid)

    print("Success:", result.success)
    print("Message:", result.message)
    print(f"Runtime: {result.metrics.runtime_seconds:.6f} sec")
    print("Nodes expanded:", result.metrics.nodes_expanded)
    print("Backtracks:", result.metrics.backtracks)

    if result.solved_grid:
        for row in result.solved_grid:
            print(row)