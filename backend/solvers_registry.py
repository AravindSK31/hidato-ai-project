from __future__ import annotations

from typing import Callable, Dict, List

from hidato_backtracking import SolverResult, HexGrid, solve_hidato_grid
from csp_solver import solve_hidato_csp_grid
from ga_solver import solve_hidato_ga_grid
from astar_solver import solve_hidato_astar_grid
from dfs_heuristic_solver import solve_hidato_dfs_heuristic_grid
SolverFn = Callable[[HexGrid], SolverResult]


SOLVER_REGISTRY: Dict[str, SolverFn] = {
    "dfs": solve_hidato_grid,
    "csp": solve_hidato_csp_grid,
    "ga": solve_hidato_ga_grid,
    "astar": solve_hidato_astar_grid,
     "dfs_heuristic": solve_hidato_dfs_heuristic_grid,
}


def get_solver(name: str) -> SolverFn:
    if name not in SOLVER_REGISTRY:
        raise ValueError(f"Unknown solver '{name}'. Available: {list(SOLVER_REGISTRY.keys())}")
    return SOLVER_REGISTRY[name]


def get_available_solvers() -> List[str]:
    return list(SOLVER_REGISTRY.keys())