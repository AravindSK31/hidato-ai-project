from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

from benchmark_runner import run_single_benchmark
from generator import generate_variant_puzzle
from solvers_registry import get_available_solvers


BoardConfig = Tuple[str, float, str, int]


@dataclass
class PuzzleAdversarialSummary:
    puzzle_id: str
    difficulty: str
    board_size: str
    board_shape: List[int]
    clue_ratio: float
    clue_count: int
    clue_pattern: str
    seed: int
    average_hardness: float
    max_hardness: float
    failures: int
    successful_runs: int
    total_runs: int
    records: List[Dict]


def hardness_score(record: Dict) -> float:
    runtime = max(float(record.get("runtime_seconds", 0.0)), 0.0)
    nodes = max(int(record.get("nodes_expanded", 0)), 0)
    backtracks = max(int(record.get("backtracks", 0)), 0)
    success = bool(record.get("success", False))

    runtime_component = 35.0 * math.log1p(runtime * 1000.0)
    nodes_component = 10.0 * math.log1p(nodes)
    backtracks_component = 8.0 * math.log1p(backtracks)

    score = runtime_component + nodes_component + backtracks_component

    if not success:
        score += 1000.0

    return score


def summarize_puzzle(records: List[Dict], seed: int) -> PuzzleAdversarialSummary:
    if not records:
        raise ValueError("Cannot summarize empty record list.")

    scores = [hardness_score(record) for record in records]
    failures = sum(1 for record in records if not record["success"])
    successes = sum(1 for record in records if record["success"])
    first = records[0]

    return PuzzleAdversarialSummary(
        puzzle_id=first["puzzle_id"],
        difficulty=first["difficulty"],
        board_size=first["board_size"],
        board_shape=first["board_shape"],
        clue_ratio=first["clue_ratio"],
        clue_count=first["clue_count"],
        clue_pattern=first["clue_pattern"],
        seed=seed,
        average_hardness=sum(scores) / len(scores),
        max_hardness=max(scores),
        failures=failures,
        successful_runs=successes,
        total_runs=len(records),
        records=records,
    )


def evaluate_single_variant(
    board_size: str,
    clue_ratio: float,
    clue_pattern: str,
    seed: int,
    algorithms: Optional[List[str]] = None,
    timeout_seconds: float = 15.0,
) -> PuzzleAdversarialSummary:
    if algorithms is None:
        algorithms = get_available_solvers()

    generated = generate_variant_puzzle(
        board_size=board_size,
        clue_ratio=clue_ratio,
        clue_pattern=clue_pattern,
        seed=seed,
    )

    puzzle_id = (
        f"adv_{board_size}_{clue_pattern}_{str(clue_ratio).replace('.', '_')}_{seed}"
    )

    metadata = {
        "puzzle_id": puzzle_id,
        "difficulty": generated.difficulty,
        "clue_count": generated.clue_count,
        "clue_ratio": generated.clue_ratio,
        "board_size": generated.board_size,
        "board_shape": generated.board_shape,
        "clue_pattern": generated.clue_pattern,
    }

    records: List[Dict] = []
    for algorithm in algorithms:
        record = run_single_benchmark(
            puzzle_grid=generated.puzzle_grid,
            algorithm=algorithm,
            metadata=metadata,
            source="adversarial",
            timeout_seconds=timeout_seconds,
            save_to_store=False,
        )
        records.append(record)

    return summarize_puzzle(records, seed=seed)


def default_search_space() -> List[BoardConfig]:
    board_sizes = ["medium", "large"]
    clue_ratios = [0.20, 0.30]
    clue_patterns = ["random", "clustered_values", "evenly_spread"]
    seeds = [1, 2]

    configs: List[BoardConfig] = []
    for board_size in board_sizes:
        for clue_ratio in clue_ratios:
            for clue_pattern in clue_patterns:
                for seed in seeds:
                    configs.append((board_size, clue_ratio, clue_pattern, seed))
    return configs


def run_adversarial_search(
    algorithms: Optional[List[str]] = None,
    configs: Optional[List[BoardConfig]] = None,
    top_k: int = 10,
    timeout_seconds: float = 15.0,
) -> Dict:
    if algorithms is None:
        algorithms = get_available_solvers()

    if configs is None:
        configs = default_search_space()

    puzzle_summaries: List[PuzzleAdversarialSummary] = []
    all_records: List[Dict] = []

    for i, (board_size, clue_ratio, clue_pattern, seed) in enumerate(configs, start=1):
        print(
            f"[{i}/{len(configs)}] Running "
            f"board={board_size}, clue_ratio={clue_ratio}, "
            f"pattern={clue_pattern}, seed={seed}"
        )

        try:
            summary = evaluate_single_variant(
                board_size=board_size,
                clue_ratio=clue_ratio,
                clue_pattern=clue_pattern,
                seed=seed,
                algorithms=algorithms,
                timeout_seconds=timeout_seconds,
            )
            puzzle_summaries.append(summary)
            all_records.extend(summary.records)

        except Exception as exc:
            print(
                f"[SKIP] board_size={board_size}, clue_ratio={clue_ratio}, "
                f"clue_pattern={clue_pattern}, seed={seed} -> {exc}"
            )

    hardest_overall = sorted(
        puzzle_summaries,
        key=lambda summary: (
            summary.failures,
            summary.average_hardness,
            summary.max_hardness,
        ),
        reverse=True,
    )[:top_k]

    records_by_algorithm: Dict[str, List[Dict]] = defaultdict(list)
    for record in all_records:
        records_by_algorithm[record["algorithm"]].append(record)

    hardest_by_algorithm: Dict[str, List[Dict]] = {}
    for algorithm, records in records_by_algorithm.items():
        hardest_by_algorithm[algorithm] = sorted(
            records,
            key=hardness_score,
            reverse=True,
        )[:top_k]

    total_failures = sum(1 for record in all_records if not record["success"])
    total_timeouts = sum(
        1 for record in all_records if "timeout" in str(record.get("source", ""))
    )

    return {
        "summary": {
            "config_count": len(configs),
            "total_puzzles_evaluated": len(puzzle_summaries),
            "total_solver_runs": len(all_records),
            "total_failures": total_failures,
            "total_timeouts": total_timeouts,
            "algorithms": algorithms,
            "timeout_seconds": timeout_seconds,
        },
        "all_records": all_records,
        "puzzle_summaries": [asdict(summary) for summary in puzzle_summaries],
        "hardest_overall": [asdict(summary) for summary in hardest_overall],
        "hardest_by_algorithm": hardest_by_algorithm,
    }


def print_overall_report(results: Dict, top_k: int = 10) -> None:
    hardest_overall = results["hardest_overall"]
    hardest_by_algorithm = results["hardest_by_algorithm"]

    print("\n========== HARDEST PUZZLES OVERALL ==========")
    for i, item in enumerate(hardest_overall[:top_k], start=1):
        print(
            f"{i}. puzzle_id={item['puzzle_id']} | difficulty={item['difficulty']} | "
            f"board={item['board_size']} | clue_ratio={item['clue_ratio']:.2f} | "
            f"pattern={item['clue_pattern']} | failures={item['failures']} | "
            f"avg_hardness={item['average_hardness']:.2f} | "
            f"max_hardness={item['max_hardness']:.2f} | seed={item['seed']}"
        )

    print("\n========== HARDEST PUZZLES PER ALGORITHM ==========")
    for algorithm, records in hardest_by_algorithm.items():
        print(f"\n--- {algorithm.upper()} ---")
        for i, record in enumerate(records[:top_k], start=1):
            print(
                f"{i}. puzzle_id={record['puzzle_id']} | success={record['success']} | "
                f"difficulty={record['difficulty']} | board={record['board_size']} | "
                f"clue_ratio={record['clue_ratio']:.2f} | pattern={record['clue_pattern']} | "
                f"runtime={record['runtime_seconds']:.6f} | nodes={record['nodes_expanded']} | "
                f"backtracks={record['backtracks']} | score={hardness_score(record):.2f}"
            )


if __name__ == "__main__":
    results = run_adversarial_search(top_k=10)
    print_overall_report(results, top_k=10)