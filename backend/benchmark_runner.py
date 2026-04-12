from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from multiprocessing import Process, Queue
import traceback

from analysis_store import save_result
from generator import generate_variant_puzzle, generate_by_difficulty
from solvers_registry import get_available_solvers, get_solver


def _solver_worker(solver_name: str, puzzle_grid, queue: Queue) -> None:
    try:
        solver_fn = get_solver(solver_name)
        result = solver_fn(puzzle_grid)
        queue.put(
            {
                "success": result.success,
                "runtime_seconds": result.metrics.runtime_seconds,
                "nodes_expanded": result.metrics.nodes_expanded,
                "backtracks": result.metrics.backtracks,
            }
        )
    except Exception as exc:
        queue.put(
            {
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
        )


def run_single_benchmark(
    puzzle_grid,
    algorithm: str,
    metadata: Dict,
    source: str = "batch",
    timeout_seconds: float = 20.0,
    save_to_store: bool = True,
) -> Dict:
    queue: Queue = Queue()
    process = Process(target=_solver_worker, args=(algorithm, puzzle_grid, queue))
    process.start()
    process.join(timeout_seconds)

    if process.is_alive():
        process.terminate()
        process.join()

        record = {
            "puzzle_id": metadata["puzzle_id"],
            "difficulty": metadata.get("difficulty", "unknown"),
            "algorithm": algorithm,
            "success": False,
            "runtime_seconds": timeout_seconds,
            "nodes_expanded": -1,
            "backtracks": -1,
            "clue_count": metadata.get("clue_count", 0),
            "clue_ratio": metadata.get("clue_ratio", 0.0),
            "board_size": metadata.get("board_size", "unknown"),
            "board_shape": metadata.get("board_shape", []),
            "clue_pattern": metadata.get("clue_pattern", "unknown"),
            "source": f"{source}_timeout",
            "timestamp": datetime.utcnow().isoformat(),
        }

        if save_to_store:
            save_result(record)
        return record

    if queue.empty():
        record = {
            "puzzle_id": metadata["puzzle_id"],
            "difficulty": metadata.get("difficulty", "unknown"),
            "algorithm": algorithm,
            "success": False,
            "runtime_seconds": 0.0,
            "nodes_expanded": -1,
            "backtracks": -1,
            "clue_count": metadata.get("clue_count", 0),
            "clue_ratio": metadata.get("clue_ratio", 0.0),
            "board_size": metadata.get("board_size", "unknown"),
            "board_shape": metadata.get("board_shape", []),
            "clue_pattern": metadata.get("clue_pattern", "unknown"),
            "source": f"{source}_error",
            "timestamp": datetime.utcnow().isoformat(),
        }

        if save_to_store:
            save_result(record)
        return record

    result_data = queue.get()

    if "error" in result_data:
        print(f"[ERROR] Solver '{algorithm}' failed: {result_data['error']}")
        print(result_data["traceback"])

        record = {
            "puzzle_id": metadata["puzzle_id"],
            "difficulty": metadata.get("difficulty", "unknown"),
            "algorithm": algorithm,
            "success": False,
            "runtime_seconds": 0.0,
            "nodes_expanded": -1,
            "backtracks": -1,
            "clue_count": metadata.get("clue_count", 0),
            "clue_ratio": metadata.get("clue_ratio", 0.0),
            "board_size": metadata.get("board_size", "unknown"),
            "board_shape": metadata.get("board_shape", []),
            "clue_pattern": metadata.get("clue_pattern", "unknown"),
            "source": f"{source}_error",
            "timestamp": datetime.utcnow().isoformat(),
        }

        if save_to_store:
            save_result(record)
        return record

    record = {
        "puzzle_id": metadata["puzzle_id"],
        "difficulty": metadata.get("difficulty", "unknown"),
        "algorithm": algorithm,
        "success": result_data["success"],
        "runtime_seconds": result_data["runtime_seconds"],
        "nodes_expanded": result_data["nodes_expanded"],
        "backtracks": result_data["backtracks"],
        "clue_count": metadata.get("clue_count", 0),
        "clue_ratio": metadata.get("clue_ratio", 0.0),
        "board_size": metadata.get("board_size", "unknown"),
        "board_shape": metadata.get("board_shape", []),
        "clue_pattern": metadata.get("clue_pattern", "unknown"),
        "source": source,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if save_to_store:
        save_result(record)
    return record


def benchmark_generated_puzzle(
    difficulty: str,
    seed: Optional[int] = None,
    algorithms: Optional[List[str]] = None,
) -> List[Dict]:
    generated = generate_by_difficulty(difficulty, seed=seed)

    if algorithms is None:
        algorithms = get_available_solvers()

    puzzle_id = f"{difficulty}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

    metadata = {
        "puzzle_id": puzzle_id,
        "difficulty": generated.difficulty,
        "clue_count": generated.clue_count,
        "clue_ratio": generated.clue_ratio,
        "board_size": generated.board_size,
        "board_shape": generated.board_shape,
        "clue_pattern": generated.clue_pattern,
    }

    results = []
    for algorithm in algorithms:
        record = run_single_benchmark(
            puzzle_grid=generated.puzzle_grid,
            algorithm=algorithm,
            metadata=metadata,
            source="batch",
            save_to_store=True,
        )
        results.append(record)

    return results


def benchmark_custom_variant(
    board_size: str,
    clue_ratio: float,
    clue_pattern: str,
    seed: Optional[int] = None,
    algorithms: Optional[List[str]] = None,
) -> List[Dict]:
    generated = generate_variant_puzzle(
        board_size=board_size,
        clue_ratio=clue_ratio,
        clue_pattern=clue_pattern,
        seed=seed,
    )

    if algorithms is None:
        algorithms = get_available_solvers()

    puzzle_id = f"variant_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

    metadata = {
        "puzzle_id": puzzle_id,
        "difficulty": generated.difficulty,
        "clue_count": generated.clue_count,
        "clue_ratio": generated.clue_ratio,
        "board_size": generated.board_size,
        "board_shape": generated.board_shape,
        "clue_pattern": generated.clue_pattern,
    }

    results = []
    for algorithm in algorithms:
        record = run_single_benchmark(
            puzzle_grid=generated.puzzle_grid,
            algorithm=algorithm,
            metadata=metadata,
            source="batch",
            save_to_store=True,
        )
        results.append(record)

    return results


def run_small_experiment() -> List[Dict]:
    all_records: List[Dict] = []

    for difficulty in ["easy", "medium", "hard"]:
        records = benchmark_generated_puzzle(difficulty=difficulty)
        all_records.extend(records)

    return all_records


if __name__ == "__main__":
    records = run_small_experiment()
    print(f"Saved {len(records)} benchmark records.")
    for r in records:
        print(
            r["algorithm"],
            r["difficulty"],
            r["success"],
            f"runtime={r['runtime_seconds']:.6f}",
            f"nodes={r['nodes_expanded']}",
            f"backtracks={r['backtracks']}",
        )