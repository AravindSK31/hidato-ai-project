import React, { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  RotateCcw,
  Shuffle,
  CheckCircle2,
  Bot,
  Loader2,
} from "lucide-react";

type CellValue = number | null;
type HexGrid = CellValue[][];

type PuzzleConfig = {
  name: "Easy" | "Medium" | "Hard";
  grid: HexGrid;
  cellWidth: number;
  cellHeight: number;
  overlap: number;
};

type SolveApiResponse = {
  success: boolean;
  solved_grid: HexGrid | null;
  runtime_seconds: number;
  nodes_expanded: number;
  backtracks: number;
  message: string;
};

type GenerateApiResponse = {
  difficulty: string;
  puzzle_grid: HexGrid;
  solution_grid: HexGrid;
  clue_count: number;
  solvable: boolean;
  message: string;
};

type SolverMetrics = {
  runtime_seconds: number;
  nodes_expanded: number;
  backtracks: number;
} | null;

type SolverMethod = "dfs" | "csp" | null;

const puzzles: Record<"Easy" | "Medium" | "Hard", PuzzleConfig> = {
  Easy: {
    name: "Easy",
    cellWidth: 62,
    cellHeight: 70,
    overlap: 18,
    grid: [
      [1, null, 3],
      [12, null, null, 4],
      [null, null, null, 15, 5],
      [10, null, 16, null],
      [null, 8, 7],
    ],
  },
  Medium: {
    name: "Medium",
    cellWidth: 68,
    cellHeight: 76,
    overlap: 20,
    grid: [
      [null, null, 4, null],
      [1, null, null, null, 8],
      [null, 11, null, null, null, null],
      [null, null, 15, null, 18],
      [null, null, null, null],
    ],
  },
  Hard: {
    name: "Hard",
    cellWidth: 72,
    cellHeight: 80,
    overlap: 22,
    grid: [
      [null, null, null, null, null],
      [null, 8, null, null, null, 14],
      [1, null, null, 18, null, null, null],
      [null, null, 22, null, null, 26, null, null],
      [null, 30, null, null, 33, null, null],
      [null, null, null, 37, null, 40],
      [null, 43, null, null, null],
    ],
  },
};

function cloneGrid(grid: HexGrid): HexGrid {
  return grid.map((row) => [...row]);
}

function getGivenMask(grid: HexGrid): boolean[][] {
  return grid.map((row) => row.map((cell) => cell !== null));
}

function getExpectedRange(grid: HexGrid): number {
  return grid.flat().length;
}

function countFilled(grid: HexGrid): number {
  return grid.flat().filter((v) => v !== null).length;
}

function hasDuplicates(grid: HexGrid): boolean {
  const seen = new Set<number>();

  for (const row of grid) {
    for (const cell of row) {
      if (cell === null) continue;
      if (seen.has(cell)) return true;
      seen.add(cell);
    }
  }

  return false;
}

function randomizeBoard(baseGrid: HexGrid, givenMask: boolean[][]): HexGrid {
  const size = getExpectedRange(baseGrid);
  const values: number[] = [];

  for (let i = 1; i <= size; i++) values.push(i);

  const shuffled = [...values].sort(() => Math.random() - 0.5);
  let idx = 0;

  return baseGrid.map((row, r) =>
    row.map((cell, c) => {
      if (givenMask[r][c]) return cell;
      return shuffled[idx++] ?? null;
    })
  );
}

function getAdjacentCoords(
  grid: HexGrid,
  r: number,
  c: number
): Array<[number, number]> {
  const neighbors: Array<[number, number]> = [];
  const currentLen = grid[r].length;

  if (c - 1 >= 0) neighbors.push([r, c - 1]);
  if (c + 1 < currentLen) neighbors.push([r, c + 1]);

  if (r - 1 >= 0) {
    const upperLen = grid[r - 1].length;

    if (upperLen === currentLen - 1) {
      if (c - 1 >= 0 && c - 1 < upperLen) neighbors.push([r - 1, c - 1]);
      if (c >= 0 && c < upperLen) neighbors.push([r - 1, c]);
    } else if (upperLen === currentLen + 1) {
      if (c >= 0 && c < upperLen) neighbors.push([r - 1, c]);
      if (c + 1 < upperLen) neighbors.push([r - 1, c + 1]);
    } else {
      if (c >= 0 && c < upperLen) neighbors.push([r - 1, c]);
      if (c - 1 >= 0 && c - 1 < upperLen) neighbors.push([r - 1, c - 1]);
    }
  }

  if (r + 1 < grid.length) {
    const lowerLen = grid[r + 1].length;

    if (lowerLen === currentLen - 1) {
      if (c - 1 >= 0 && c - 1 < lowerLen) neighbors.push([r + 1, c - 1]);
      if (c >= 0 && c < lowerLen) neighbors.push([r + 1, c]);
    } else if (lowerLen === currentLen + 1) {
      if (c >= 0 && c < lowerLen) neighbors.push([r + 1, c]);
      if (c + 1 < lowerLen) neighbors.push([r + 1, c + 1]);
    } else {
      if (c >= 0 && c < lowerLen) neighbors.push([r + 1, c]);
      if (c - 1 >= 0 && c - 1 < lowerLen) neighbors.push([r + 1, c - 1]);
    }
  }

  const unique = new Map<string, [number, number]>();
  for (const [nr, nc] of neighbors) {
    unique.set(`${nr}-${nc}`, [nr, nc]);
  }

  return Array.from(unique.values());
}

function isHexAdjacent(
  grid: HexGrid,
  a: [number, number],
  b: [number, number]
): boolean {
  const neighbors = getAdjacentCoords(grid, a[0], a[1]);
  return neighbors.some(([nr, nc]) => nr === b[0] && nc === b[1]);
}

function validateHidato(grid: HexGrid): { ok: boolean; message: string } {
  const maxVal = getExpectedRange(grid);
  const positions = new Map<number, [number, number]>();

  for (let r = 0; r < grid.length; r++) {
    for (let c = 0; c < grid[r].length; c++) {
      const value = grid[r][c];

      if (value === null) continue;

      if (value < 1 || value > maxVal) {
        return { ok: false, message: `Value ${value} is out of range 1-${maxVal}.` };
      }

      if (positions.has(value)) {
        return { ok: false, message: `Duplicate value ${value} found.` };
      }

      positions.set(value, [r, c]);
    }
  }

  for (let i = 1; i <= maxVal; i++) {
    if (!positions.has(i)) {
      return { ok: false, message: `Missing value ${i}.` };
    }
  }

  for (let i = 1; i < maxVal; i++) {
    const current = positions.get(i);
    const next = positions.get(i + 1);

    if (!current || !next) {
      return { ok: false, message: `Missing value ${i} or ${i + 1}.` };
    }

    if (!isHexAdjacent(grid, current, next)) {
      return { ok: false, message: `${i} and ${i + 1} are not adjacent on the hex board.` };
    }
  }

  return { ok: true, message: "Valid Hidato path found." };
}

function getCellStyle(
  given: boolean,
  cellWidth: number,
  cellHeight: number
): React.CSSProperties {
  return {
    width: `${cellWidth}px`,
    height: `${cellHeight}px`,
    clipPath: "polygon(25% 6%, 75% 6%, 100% 50%, 75% 94%, 25% 94%, 0% 50%)",
    WebkitClipPath:
      "polygon(25% 6%, 75% 6%, 100% 50%, 75% 94%, 25% 94%, 0% 50%)",
    background: given
      ? "linear-gradient(180deg, #fde68a 0%, #fbbf24 100%)"
      : "linear-gradient(180deg, #fffdf6 0%, #f5efe1 100%)",
    border: given ? "2px solid #7c5a10" : "2px solid #8b7355",
    boxShadow: given
      ? "inset 0 1px 0 rgba(255,255,255,0.55), 0 8px 18px rgba(0,0,0,0.18)"
      : "inset 0 1px 0 rgba(255,255,255,0.85), 0 8px 18px rgba(0,0,0,0.12)",
  };
}

export default function HidatoFrontendApp() {
  const [difficulty, setDifficulty] = useState<"Easy" | "Medium" | "Hard">("Easy");
  const [grid, setGrid] = useState<HexGrid>(cloneGrid(puzzles.Easy.grid));
  const [basePuzzleGrid, setBasePuzzleGrid] = useState<HexGrid>(
    cloneGrid(puzzles.Easy.grid)
  );
  const [status, setStatus] = useState<string>(
    "Fill the board so consecutive numbers touch through hex neighbors."
  );
  const [solverLoading, setSolverLoading] = useState(false);
  const [generatorLoading, setGeneratorLoading] = useState(false);
  const [solverMetrics, setSolverMetrics] = useState<SolverMetrics>(null);
  const [activeSolver, setActiveSolver] = useState<SolverMethod>(null);

  const puzzle = useMemo(() => puzzles[difficulty], [difficulty]);
  const givenMask = useMemo(() => getGivenMask(basePuzzleGrid), [basePuzzleGrid]);
  const totalPlayable = useMemo(() => getExpectedRange(basePuzzleGrid), [basePuzzleGrid]);
  const filledCount = countFilled(grid);
  const duplicateWarning = hasDuplicates(grid);

  const loadDifficulty = async (level: "Easy" | "Medium" | "Hard") => {
    try {
      setGeneratorLoading(true);
      setStatus(`Generating ${level} puzzle...`);
      setSolverMetrics(null);
      setActiveSolver(null);

      const response = await fetch(
        `http://127.0.0.1:8000/generate?difficulty=${level.toLowerCase()}`
      );

      const data: GenerateApiResponse = await response.json();

      if (data.solvable && data.puzzle_grid && data.puzzle_grid.length > 0) {
        setDifficulty(level);
        setBasePuzzleGrid(cloneGrid(data.puzzle_grid));
        setGrid(cloneGrid(data.puzzle_grid));
        setStatus(data.message || `${level} puzzle generated.`);
      } else {
        setStatus(data.message || `Could not generate ${level} puzzle.`);
      }
    } catch (error) {
      console.error("Backend generator error:", error);
      setStatus("Could not connect to backend generator. Make sure FastAPI is running.");
    } finally {
      setGeneratorLoading(false);
    }
  };

  useEffect(() => {
    loadDifficulty("Easy");
  }, []);

  const handleCellChange = (r: number, c: number, raw: string) => {
    const value: CellValue = raw === "" ? null : Number(raw);

    setGrid((prev) => {
      const next = cloneGrid(prev);
      if (givenMask[r][c]) return prev;
      next[r][c] = Number.isNaN(value as number) ? null : value;
      return next;
    });
  };

  const resetBoard = () => {
    setGrid(cloneGrid(basePuzzleGrid));
    setSolverMetrics(null);
    setActiveSolver(null);
    setStatus(`${difficulty} puzzle reset.`);
  };

  const fillDemo = () => {
    setGrid(randomizeBoard(basePuzzleGrid, givenMask));
    setSolverMetrics(null);
    setActiveSolver(null);
    setStatus("Demo fill applied. This is only for UI testing, not a real solution.");
  };

  const checkBoard = () => {
    const result = validateHidato(grid);
    setStatus(result.message);
  };

  const solveWithMethod = async (method: "dfs" | "csp") => {
    setSolverLoading(true);
    setActiveSolver(method);
    setStatus(
      method === "dfs"
        ? "Solving puzzle using DFS backtracking..."
        : "Solving puzzle using CSP with propagation..."
    );
    setSolverMetrics(null);

    try {
      const response = await fetch("http://127.0.0.1:8000/solve", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          grid,
          method,
        }),
      });

      const data: SolveApiResponse = await response.json();

      if (data.success && data.solved_grid) {
        setGrid(data.solved_grid);
        setSolverMetrics({
          runtime_seconds: data.runtime_seconds,
          nodes_expanded: data.nodes_expanded,
          backtracks: data.backtracks,
        });
        setStatus(
          data.message ||
            (method === "dfs"
              ? "Puzzle solved successfully with DFS."
              : "Puzzle solved successfully with CSP.")
        );
      } else {
        setStatus(
          data.message ||
            (method === "dfs"
              ? "DFS could not solve this puzzle."
              : "CSP could not solve this puzzle.")
        );
      }
    } catch (error) {
      console.error("Backend solver error:", error);
      setStatus("Could not connect to backend solver. Make sure FastAPI is running.");
    } finally {
      setSolverLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#2d1b12_0%,#16110d_45%,#0b0907_100%)] text-white">
      <div className="max-w-7xl mx-auto px-4 py-6 md:px-8 md:py-10">
        <div className="grid gap-6 lg:grid-cols-[1.18fr_0.82fr]">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
            <Card className="overflow-hidden rounded-[28px] border border-amber-900/30 bg-[linear-gradient(180deg,rgba(64,39,24,0.94)_0%,rgba(32,21,15,0.97)_100%)] shadow-[0_25px_80px_rgba(0,0,0,0.45)]">
              <CardHeader className="border-b border-amber-900/20 bg-[linear-gradient(180deg,rgba(120,75,40,0.22)_0%,rgba(0,0,0,0)_100%)]">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <CardTitle className="text-3xl font-bold tracking-tight text-amber-50">
                      Hidato Solver Playground
                    </CardTitle>
                    <CardDescription className="mt-2 text-amber-100/80 text-base">
                      A polished hex-board version for your AI project.
                    </CardDescription>
                  </div>
                  <Badge className="rounded-full border border-amber-800 bg-amber-200/90 px-4 py-1 text-amber-950 shadow">
                    {difficulty}
                  </Badge>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  <Button
                    onClick={() => loadDifficulty("Easy")}
                    disabled={generatorLoading || solverLoading}
                    variant={difficulty === "Easy" ? "default" : "outline"}
                    className={`rounded-full px-5 ${
                      difficulty === "Easy"
                        ? "bg-amber-300 text-amber-950 hover:bg-amber-200"
                        : "border-amber-700/60 bg-transparent text-amber-100 hover:bg-amber-900/30"
                    }`}
                  >
                    Easy
                  </Button>
                  <Button
                    onClick={() => loadDifficulty("Medium")}
                    disabled={generatorLoading || solverLoading}
                    variant={difficulty === "Medium" ? "default" : "outline"}
                    className={`rounded-full px-5 ${
                      difficulty === "Medium"
                        ? "bg-amber-300 text-amber-950 hover:bg-amber-200"
                        : "border-amber-700/60 bg-transparent text-amber-100 hover:bg-amber-900/30"
                    }`}
                  >
                    Medium
                  </Button>
                  <Button
                    onClick={() => loadDifficulty("Hard")}
                    disabled={generatorLoading || solverLoading}
                    variant={difficulty === "Hard" ? "default" : "outline"}
                    className={`rounded-full px-5 ${
                      difficulty === "Hard"
                        ? "bg-amber-300 text-amber-950 hover:bg-amber-200"
                        : "border-amber-700/60 bg-transparent text-amber-100 hover:bg-amber-900/30"
                    }`}
                  >
                    Hard
                  </Button>
                </div>

                <div className="mt-4 flex flex-wrap gap-3">
                  <Button
                    onClick={resetBoard}
                    disabled={generatorLoading || solverLoading}
                    className="rounded-full bg-amber-100 text-stone-900 hover:bg-white"
                  >
                    <RotateCcw className="mr-2 h-4 w-4" /> Reset
                  </Button>
                  <Button
                    onClick={fillDemo}
                    disabled={generatorLoading || solverLoading}
                    variant="secondary"
                    className="rounded-full bg-stone-700 text-stone-100 hover:bg-stone-600"
                  >
                    <Shuffle className="mr-2 h-4 w-4" /> Demo Fill
                  </Button>
                  <Button
                    onClick={checkBoard}
                    disabled={generatorLoading || solverLoading}
                    variant="outline"
                    className="rounded-full border-amber-700/60 bg-transparent text-amber-100 hover:bg-amber-900/30"
                  >
                    <CheckCircle2 className="mr-2 h-4 w-4" /> Check Board
                  </Button>
                  <Button
                    onClick={() => solveWithMethod("dfs")}
                    disabled={solverLoading || generatorLoading}
                    className="rounded-full bg-emerald-500 text-white hover:bg-emerald-400 disabled:opacity-70"
                  >
                    {solverLoading && activeSolver === "dfs" ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Solving DFS...
                      </>
                    ) : (
                      <>
                        <Bot className="mr-2 h-4 w-4" />
                        Solve with DFS
                      </>
                    )}
                  </Button>
                  <Button
                    onClick={() => solveWithMethod("csp")}
                    disabled={solverLoading || generatorLoading}
                    className="rounded-full bg-sky-500 text-white hover:bg-sky-400 disabled:opacity-70"
                  >
                    {solverLoading && activeSolver === "csp" ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Solving CSP...
                      </>
                    ) : (
                      <>
                        <Bot className="mr-2 h-4 w-4" />
                        Solve with CSP
                      </>
                    )}
                  </Button>
                </div>
              </CardHeader>

              <CardContent className="p-4 md:p-6">
                <div className="rounded-[28px] border border-[#695338] bg-[linear-gradient(180deg,#8c6a3a_0%,#6c4f2a_100%)] p-4 shadow-[inset_0_2px_14px_rgba(255,255,255,0.08)] md:p-6">
                  <div className="rounded-[24px] border border-black/15 bg-[radial-gradient(circle_at_top,#b08852_0%,#8d6738_35%,#6b4f2b_100%)] p-3 md:p-5">
                    <div className="min-w-[500px]">
                      {grid.map((row, r) => (
                        <div
                          key={`row-${r}`}
                          className="flex justify-center gap-1.5"
                          style={{
                            marginTop: r === 0 ? "0px" : `-${puzzle.overlap}px`,
                          }}
                        >
                          {row.map((cell, c) => {
                            const given = givenMask[r][c];

                            return (
                              <motion.div
                                key={`${r}-${c}`}
                                whileHover={{ scale: 1.05, y: -2 }}
                                className="relative flex items-center justify-center transition-all"
                                style={getCellStyle(given, puzzle.cellWidth, puzzle.cellHeight)}
                              >
                                <div
                                  className="absolute inset-[6px] opacity-20"
                                  style={{
                                    clipPath:
                                      "polygon(25% 6%, 75% 6%, 100% 50%, 75% 94%, 25% 94%, 0% 50%)",
                                    WebkitClipPath:
                                      "polygon(25% 6%, 75% 6%, 100% 50%, 75% 94%, 25% 94%, 0% 50%)",
                                    background:
                                      "linear-gradient(180deg, rgba(255,255,255,0.65) 0%, rgba(255,255,255,0) 70%)",
                                  }}
                                />
                                {given ? (
                                  <div className="relative text-[22px] font-bold text-stone-900 md:text-[26px]">
                                    {cell}
                                  </div>
                                ) : (
                                  <input
                                    type="number"
                                    min={1}
                                    max={totalPlayable}
                                    value={cell ?? ""}
                                    onChange={(e) => handleCellChange(r, c, e.target.value)}
                                    className="relative h-full w-full bg-transparent text-center text-[20px] font-semibold text-stone-900 outline-none md:text-[24px]"
                                  />
                                )}
                              </motion.div>
                            );
                          })}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-6"
          >
            <Card className="rounded-[26px] border border-amber-900/25 bg-[linear-gradient(180deg,rgba(55,35,24,0.96)_0%,rgba(25,18,14,0.98)_100%)] shadow-[0_18px_50px_rgba(0,0,0,0.35)]">
              <CardHeader>
                <CardTitle className="text-xl text-amber-50">Game Rules</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-amber-100/85 leading-7">
                <p>Fill the board with consecutive numbers from 1 to {totalPlayable}.</p>
                <p>Each number must touch the next one through hex-cell neighbors.</p>
                <p>Gold cells are fixed clues. Ivory cells are editable.</p>
              </CardContent>
            </Card>

            <Card className="rounded-[26px] border border-amber-900/25 bg-[linear-gradient(180deg,rgba(55,35,24,0.96)_0%,rgba(25,18,14,0.98)_100%)] shadow-[0_18px_50px_rgba(0,0,0,0.35)]">
              <CardHeader>
                <CardTitle className="text-xl text-amber-50">Progress</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between text-sm text-amber-100/80">
                  <span>Filled cells</span>
                  <span>
                    {filledCount} / {totalPlayable}
                  </span>
                </div>

                <div className="h-3 w-full overflow-hidden rounded-full bg-stone-800">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-amber-300 to-yellow-500 transition-all"
                    style={{ width: `${(filledCount / totalPlayable) * 100}%` }}
                  />
                </div>

                <div className="rounded-2xl border border-amber-900/20 bg-black/20 p-4 text-sm leading-6 text-amber-100/85">
                  {status}
                </div>

                {duplicateWarning && (
                  <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
                    Duplicate numbers detected on the board.
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="rounded-[26px] border border-amber-900/25 bg-[linear-gradient(180deg,rgba(55,35,24,0.96)_0%,rgba(25,18,14,0.98)_100%)] shadow-[0_18px_50px_rgba(0,0,0,0.35)]">
              <CardHeader>
                <CardTitle className="text-xl text-amber-50">
                  {activeSolver
                    ? `${activeSolver.toUpperCase()} Solver Metrics`
                    : "Solver Metrics"}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-amber-100/85 leading-7">
                {solverMetrics ? (
                  <>
                    <p>Runtime: {solverMetrics.runtime_seconds.toFixed(6)} seconds</p>
                    <p>Nodes Expanded: {solverMetrics.nodes_expanded}</p>
                    <p>Backtracks: {solverMetrics.backtracks}</p>
                  </>
                ) : (
                  <p>No solver run yet. Click “Solve with DFS” or “Solve with CSP” to view metrics.</p>
                )}
              </CardContent>
            </Card>

            <Card className="rounded-[26px] border border-amber-900/25 bg-[linear-gradient(180deg,rgba(55,35,24,0.96)_0%,rgba(25,18,14,0.98)_100%)] shadow-[0_18px_50px_rgba(0,0,0,0.35)]">
              <CardHeader>
                <CardTitle className="text-xl text-amber-50">Difficulty Notes</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-amber-100/85 leading-7">
                <p>Easy: smaller board, more guided clues.</p>
                <p>Medium: wider board with fewer fixed numbers.</p>
                <p>Hard: larger board and sparser clues.</p>
                <p>Analysis comparisons across all algorithms can go on a separate page.</p>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>
    </div>
  );
}