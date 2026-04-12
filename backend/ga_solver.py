from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import random
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


@dataclass
class GAConfig:
    population_size: int = 100
    max_generations: int = 500
    mutation_rate: float = 0.2
    crossover_rate: float = 0.9
    elite_count: int = 2
    tournament_size: int = 3
    stagnation_limit: int = 100
    random_seed: Optional[int] = None


@dataclass
class Individual:
    chromosome: List[CellId]
    penalty: int


class HidatoGeneticSolver:
    def __init__(self, puzzle: HidatoPuzzle, config: Optional[GAConfig] = None):
        self.puzzle = puzzle
        self.N = puzzle.total_numbers
        self.config = config or GAConfig()
        self.rng = random.Random(self.config.random_seed)
        self.metrics = SolverMetrics()

        self.cell_ids = list(puzzle.cells.keys())
        self.fixed_positions = self._build_fixed_positions()
        self.neighbor_map = {
            cell_id: set(cell.neighbors)
            for cell_id, cell in puzzle.cells.items()
        }

        self.fitness_evaluations = 0

    def _build_fixed_positions(self) -> Dict[int, CellId]:
        """
        value_index -> required cell_id
        value_index is 0-based, so value k sits at index k-1
        """
        fixed = {}
        for value, cell_id in self.puzzle.fixed_values.items():
            fixed[value - 1] = cell_id
        return fixed

    def solve(self) -> SolverResult:
        start = time.perf_counter()

        population = self._initialize_population()
        best = min(population, key=lambda ind: ind.penalty)

        generations_without_improvement = 0

        for generation in range(self.config.max_generations):
            if best.penalty == 0:
                break

            new_population = self._elitism(population)

            while len(new_population) < self.config.population_size:
                parent1 = self._tournament_select(population)
                parent2 = self._tournament_select(population)

                if self.rng.random() < self.config.crossover_rate:
                    child1, child2 = self._crossover(parent1, parent2)
                else:
                    child1 = parent1.chromosome[:]
                    child2 = parent2.chromosome[:]

                if self.rng.random() < self.config.mutation_rate:
                    self._mutate(child1)
                if self.rng.random() < self.config.mutation_rate:
                    self._mutate(child2)

                self._repair_fixed_positions(child1)
                self._repair_fixed_positions(child2)

                new_population.append(
                    Individual(child1, self._evaluate(child1))
                )
                if len(new_population) < self.config.population_size:
                    new_population.append(
                        Individual(child2, self._evaluate(child2))
                    )

            population = new_population
            current_best = min(population, key=lambda ind: ind.penalty)

            if current_best.penalty < best.penalty:
                best = current_best
                generations_without_improvement = 0
            else:
                generations_without_improvement += 1

            if generations_without_improvement >= self.config.stagnation_limit:
                break

        runtime = time.perf_counter() - start
        self.metrics.runtime_seconds = runtime
        self.metrics.nodes_expanded = self.fitness_evaluations
        self.metrics.backtracks = 0

        if best.penalty == 0:
            assignment = {
                cell_id: idx + 1
                for idx, cell_id in enumerate(best.chromosome)
            }
            solved_grid = grid_from_assignment(self.puzzle, assignment)
            return SolverResult(
                success=True,
                solved_grid=solved_grid,
                metrics=self.metrics,
                message="Puzzle solved successfully with Genetic Algorithm."
            )

        return SolverResult(
            success=False,
            solved_grid=None,
            metrics=self.metrics,
            message="Genetic Algorithm did not find a valid solution."
        )

    def _initialize_population(self) -> List[Individual]:
        population = []
        for _ in range(self.config.population_size):
            chromosome = self._random_chromosome()
            population.append(Individual(chromosome, self._evaluate(chromosome)))
        return population

    def _random_chromosome(self) -> List[CellId]:
        chromosome = [None] * self.N  # type: ignore

        fixed_cells = set(self.fixed_positions.values())
        free_cells = [cell for cell in self.cell_ids if cell not in fixed_cells]
        self.rng.shuffle(free_cells)

        # place fixed values
        for idx, cell_id in self.fixed_positions.items():
            chromosome[idx] = cell_id

        # fill remaining slots
        free_idx = [i for i in range(self.N) if i not in self.fixed_positions]
        for idx, cell_id in zip(free_idx, free_cells):
            chromosome[idx] = cell_id

        return chromosome  # type: ignore

    def _evaluate(self, chromosome: List[CellId]) -> int:
        self.fitness_evaluations += 1

        penalty = 0

        # fixed clue penalty
        for idx, required_cell in self.fixed_positions.items():
            if chromosome[idx] != required_cell:
                penalty += 1000

        # adjacency penalty
        for i in range(self.N - 1):
            a = chromosome[i]
            b = chromosome[i + 1]
            if b not in self.neighbor_map[a]:
                penalty += 20

        return penalty

    def _tournament_select(self, population: List[Individual]) -> Individual:
        candidates = self.rng.sample(population, self.config.tournament_size)
        return min(candidates, key=lambda ind: ind.penalty)

    def _elitism(self, population: List[Individual]) -> List[Individual]:
        sorted_pop = sorted(population, key=lambda ind: ind.penalty)
        elites = sorted_pop[: self.config.elite_count]
        return [Individual(ind.chromosome[:], ind.penalty) for ind in elites]

    def _crossover(
        self,
        parent1: Individual,
        parent2: Individual,
    ) -> Tuple[List[CellId], List[CellId]]:
        """
        Order-crossover on non-fixed positions only.
        """
        free_positions = [i for i in range(self.N) if i not in self.fixed_positions]
        if len(free_positions) < 2:
            return parent1.chromosome[:], parent2.chromosome[:]

        a, b = sorted(self.rng.sample(range(len(free_positions)), 2))
        slice_positions = free_positions[a : b + 1]

        child1 = [None] * self.N  # type: ignore
        child2 = [None] * self.N  # type: ignore

        # copy fixed positions
        for idx, cell_id in self.fixed_positions.items():
            child1[idx] = cell_id
            child2[idx] = cell_id

        # copy slice from each parent
        used1 = set(self.fixed_positions.values())
        used2 = set(self.fixed_positions.values())

        for idx in slice_positions:
            child1[idx] = parent1.chromosome[idx]
            child2[idx] = parent2.chromosome[idx]
            used1.add(parent1.chromosome[idx])
            used2.add(parent2.chromosome[idx])

        # fill remaining from opposite parent order
        p2_free_cells = [c for i, c in enumerate(parent2.chromosome) if c not in used1]
        p1_free_cells = [c for i, c in enumerate(parent1.chromosome) if c not in used2]

        fill_positions = [i for i in free_positions if i not in slice_positions]

        for idx, cell_id in zip(fill_positions, p2_free_cells):
            child1[idx] = cell_id
        for idx, cell_id in zip(fill_positions, p1_free_cells):
            child2[idx] = cell_id

        return child1, child2  # type: ignore

    def _mutate(self, chromosome: List[CellId]) -> None:
        free_positions = [i for i in range(self.N) if i not in self.fixed_positions]
        if len(free_positions) < 2:
            return

        i, j = self.rng.sample(free_positions, 2)
        chromosome[i], chromosome[j] = chromosome[j], chromosome[i]

    def _repair_fixed_positions(self, chromosome: List[CellId]) -> None:
        """
        Ensure fixed values are in the correct indices and uniqueness is preserved.
        """
        for idx, required_cell in self.fixed_positions.items():
            if chromosome[idx] == required_cell:
                continue

            # find where the required cell currently is
            current_pos = chromosome.index(required_cell)
            chromosome[current_pos], chromosome[idx] = chromosome[idx], chromosome[current_pos]


def solve_hidato_ga_grid(grid: HexGrid) -> SolverResult:
    puzzle = build_puzzle(grid)
    solver = HidatoGeneticSolver(puzzle)
    return solver.solve()


if __name__ == "__main__":
    test_grid = [
        [1, None, 3],
        [12, None, None, 4],
        [None, None, None, 15, 5],
        [10, None, 16, None],
        [None, 8, 7],
    ]

    result = solve_hidato_ga_grid(test_grid)
    print("Success:", result.success)
    print("Message:", result.message)
    print("Runtime:", result.metrics.runtime_seconds)
    print("Fitness evaluations:", result.metrics.nodes_expanded)