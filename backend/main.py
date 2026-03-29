from typing import List, Optional, Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from hidato_backtracking import solve_hidato_grid
from generator import generate_by_difficulty

from csp_solver import solve_hidato_csp_grid
GridType = List[List[Optional[int]]]

from datetime import datetime
from analysis_store import load_results, save_result

# -----------------------------
# Request / Response models
# -----------------------------

class SolveRequest(BaseModel):
    grid: GridType
    method: Literal["dfs", "csp"] = "dfs"

class SolveResponse(BaseModel):
    success: bool
    solved_grid: Optional[GridType]
    runtime_seconds: float
    nodes_expanded: int
    backtracks: int
    message: str


class GenerateResponse(BaseModel):
    difficulty: str
    puzzle_grid: GridType
    solution_grid: GridType
    clue_count: int
    clue_ratio: float
    solvable: bool
    board_size: str
    board_shape: List[int]
    clue_pattern: str
    message: str

class ResultRecord(BaseModel):
    puzzle_id: str
    difficulty: str
    algorithm: str
    success: bool
    runtime_seconds: float
    nodes_expanded: int
    backtracks: int
    clue_count: int
    clue_ratio: float
    board_size: str
    board_shape: List[int]
    clue_pattern: str
    source: str
    timestamp: str

# -----------------------------
# FastAPI App
# -----------------------------

app = FastAPI(title="Hidato Solver API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Root / health route
# -----------------------------

@app.get("/")
def root():
    return {"message": "Hidato Solver API running"}


# -----------------------------
# Solve endpoint
# -----------------------------

@app.post("/solve", response_model=SolveResponse)
def solve_puzzle(request: SolveRequest):
    try:
        if request.method == "dfs":
            result = solve_hidato_grid(request.grid)
        elif request.method == "csp":
            result = solve_hidato_csp_grid(request.grid)
        else:
            return SolveResponse(
                success=False,
                solved_grid=None,
                runtime_seconds=0.0,
                nodes_expanded=0,
                backtracks=0,
                message=f"Method '{request.method}' not implemented yet",
            )

        clue_count = sum(
            1 for row in request.grid for cell in row if cell is not None
        )
        total_cells = sum(len(row) for row in request.grid)
        clue_ratio = clue_count / total_cells if total_cells > 0 else 0.0
        board_shape = [len(row) for row in request.grid]

        if total_cells <= 19:
            board_size = "small"
        elif total_cells <= 24:
            board_size = "medium"
        else:
            board_size = "large"

        puzzle_id = f"{request.method}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

        save_result({
            "puzzle_id": puzzle_id,
            "difficulty": "unknown",
            "algorithm": request.method,
            "success": result.success,
            "runtime_seconds": result.metrics.runtime_seconds,
            "nodes_expanded": result.metrics.nodes_expanded,
            "backtracks": result.metrics.backtracks,
            "clue_count": clue_count,
            "clue_ratio": clue_ratio,
            "board_size": board_size,
            "board_shape": board_shape,
            "clue_pattern": "unknown",
            "source": "ui",
            "timestamp": datetime.utcnow().isoformat(),
        })

        return SolveResponse(
            success=result.success,
            solved_grid=result.solved_grid,
            runtime_seconds=result.metrics.runtime_seconds,
            nodes_expanded=result.metrics.nodes_expanded,
            backtracks=result.metrics.backtracks,
            message=result.message,
        )

    except Exception as e:
        return SolveResponse(
            success=False,
            solved_grid=None,
            runtime_seconds=0.0,
            nodes_expanded=0,
            backtracks=0,
            message=f"Error: {str(e)}",
        )


# -----------------------------
# Generate endpoint
# -----------------------------

@app.get("/generate", response_model=GenerateResponse)
def generate_puzzle(difficulty: Literal["easy", "medium", "hard"] = "easy"):
    try:
        generated = generate_by_difficulty(difficulty)

        return GenerateResponse(
            difficulty=generated.difficulty,
            puzzle_grid=generated.puzzle_grid,
            solution_grid=generated.solution_grid,
            clue_count=generated.clue_count,
            clue_ratio=generated.clue_ratio,
            solvable=generated.solvable,
            board_size=generated.board_size,
            board_shape=generated.board_shape,
            clue_pattern=generated.clue_pattern,
            message=f"{generated.difficulty.capitalize()} puzzle generated successfully.",
        )

    except Exception as e:
        return GenerateResponse(
            difficulty=difficulty,
            puzzle_grid=[],
            solution_grid=[],
            clue_count=0,
            clue_ratio=0.0,
            solvable=False,
            board_size="unknown",
            board_shape=[],
            clue_pattern="unknown",
            message=f"Error: {str(e)}",
        )
    
@app.get("/results")
def get_results():
    return load_results()