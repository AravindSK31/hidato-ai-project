import React, { useMemo, useState } from "react";
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
import { RotateCcw, Shuffle, CheckCircle2 } from "lucide-react";

type CellValue = number | null;
type HexGrid = CellValue[][];

type PuzzleConfig = {
  name: "Easy" | "Medium" | "Hard";
  grid: HexGrid;
  cellWidth: number;
  cellHeight: number;
  overlap: number;
};

const puzzles: Record<"Easy" | "Medium" | "Hard", PuzzleConfig> = {
  Easy: {
    name: "Easy",
    cellWidth: 64,
    cellHeight: 72,
    overlap: 18,
    grid: [
      [null, 3, null],
      [1, null, 5, null],
      [null, null, null, 7, null],
      [null, 9, null, null],
      [null, 11, null],
    ],
  },
  Medium: {
    name: "Medium",
    cellWidth: 70,
    cellHeight: 78,
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
    cellWidth: 74,
    cellHeight: 82,
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

function getAdjacentCoords(grid: HexGrid, r: number, c: number): Array<[number, number]> {
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

function isHexAdjacent(grid: HexGrid, a: [number, number], b: [number, number]): boolean {
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
    background: given ? "rgba(186, 230, 253, 0.95)" : "rgba(255,255,255,0.95)",
    border: "2px solid #111827",
    boxShadow: "0 6px 18px rgba(0,0,0,0.18)",
  };
}

export default function HidatoFrontendApp() {
  const [difficulty, setDifficulty] = useState<"Easy" | "Medium" | "Hard">("Easy");

  const puzzle = useMemo(() => puzzles[difficulty], [difficulty]);
  const [grid, setGrid] = useState<HexGrid>(cloneGrid(puzzles.Easy.grid));
  const [status, setStatus] = useState<string>(
    "Fill the hex board so consecutive numbers touch through hex neighbors."
  );

  const givenMask = useMemo(() => getGivenMask(puzzle.grid), [puzzle]);
  const totalPlayable = useMemo(() => getExpectedRange(puzzle.grid), [puzzle]);
  const filledCount = countFilled(grid);
  const duplicateWarning = hasDuplicates(grid);

  const loadDifficulty = (level: "Easy" | "Medium" | "Hard") => {
    setDifficulty(level);
    setGrid(cloneGrid(puzzles[level].grid));
    setStatus(`${level} puzzle loaded.`);
  };

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
    setGrid(cloneGrid(puzzle.grid));
    setStatus(`${difficulty} puzzle reset.`);
  };

  const fillDemo = () => {
    setGrid(randomizeBoard(puzzle.grid, givenMask));
    setStatus("Demo fill applied. This is only for UI testing, not a real solution.");
  };

  const checkBoard = () => {
    const result = validateHidato(grid);
    setStatus(result.message);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white p-4 md:p-8">
      <div className="max-w-7xl mx-auto grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="rounded-3xl border-slate-800 bg-slate-900/90 shadow-2xl">
            <CardHeader className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <CardTitle className="text-3xl font-bold tracking-tight">
                    Hidato Solver Playground
                  </CardTitle>
                  <CardDescription className="text-slate-300 mt-2 text-base">
                    Hex board UI with multiple difficulty levels.
                  </CardDescription>
                </div>
                <Badge className="rounded-full px-4 py-1 text-sm">
                  {difficulty}
                </Badge>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={() => loadDifficulty("Easy")}
                  variant={difficulty === "Easy" ? "default" : "outline"}
                  className="rounded-2xl"
                >
                  Easy
                </Button>
                <Button
                  onClick={() => loadDifficulty("Medium")}
                  variant={difficulty === "Medium" ? "default" : "outline"}
                  className="rounded-2xl"
                >
                  Medium
                </Button>
                <Button
                  onClick={() => loadDifficulty("Hard")}
                  variant={difficulty === "Hard" ? "default" : "outline"}
                  className="rounded-2xl"
                >
                  Hard
                </Button>
              </div>

              <div className="flex flex-wrap gap-3">
                <Button onClick={resetBoard} className="rounded-2xl">
                  <RotateCcw className="mr-2 h-4 w-4" /> Reset
                </Button>
                <Button onClick={fillDemo} variant="secondary" className="rounded-2xl">
                  <Shuffle className="mr-2 h-4 w-4" /> Demo Fill
                </Button>
                <Button
                  onClick={checkBoard}
                  variant="outline"
                  className="rounded-2xl border-slate-700 bg-transparent text-white hover:bg-slate-800"
                >
                  <CheckCircle2 className="mr-2 h-4 w-4" /> Check Board
                </Button>
              </div>
            </CardHeader>

            <CardContent>
              <div className="rounded-[28px] border border-slate-800 bg-[#6b6f00] p-4 md:p-5 overflow-x-auto">
                <div className="min-w-[520px]">
                  {grid.map((row, r) => (
                    <div
                      key={`row-${r}`}
                      className={`flex justify-center gap-1.5 ${
                        r === 0 ? "" : ""
                      }`}
                      style={{
                        marginTop: r === 0 ? "0px" : `-${puzzle.overlap}px`,
                      }}
                    >
                      {row.map((cell, c) => {
                        const given = givenMask[r][c];

                        return (
                          <motion.div
                            key={`${r}-${c}`}
                            whileHover={{ scale: 1.04 }}
                            className="relative flex items-center justify-center"
                            style={getCellStyle(given, puzzle.cellWidth, puzzle.cellHeight)}
                          >
                            {given ? (
                              <div className="text-[22px] md:text-[26px] font-semibold text-slate-950">
                                {cell}
                              </div>
                            ) : (
                              <input
                                type="number"
                                min={1}
                                max={totalPlayable}
                                value={cell ?? ""}
                                onChange={(e) => handleCellChange(r, c, e.target.value)}
                                className="h-full w-full bg-transparent text-center text-[20px] md:text-[24px] font-semibold text-slate-950 outline-none [appearance:textfield]"
                              />
                            )}
                          </motion.div>
                        );
                      })}
                    </div>
                  ))}
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
          <Card className="rounded-3xl border-slate-800 bg-slate-900/90 shadow-2xl">
            <CardHeader>
              <CardTitle className="text-xl">Game Rules</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-slate-300 leading-7">
              <p>Fill the board with consecutive numbers from 1 to {totalPlayable}.</p>
              <p>Each number must touch the next one through hex-cell neighbors.</p>
              <p>Blue cells are fixed clues. White cells are editable.</p>
            </CardContent>
          </Card>

          <Card className="rounded-3xl border-slate-800 bg-slate-900/90 shadow-2xl">
            <CardHeader>
              <CardTitle className="text-xl">Progress</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between text-sm text-slate-300">
                <span>Filled cells</span>
                <span>
                  {filledCount} / {totalPlayable}
                </span>
              </div>

              <div className="h-3 w-full rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full rounded-full bg-cyan-300 transition-all"
                  style={{ width: `${(filledCount / totalPlayable) * 100}%` }}
                />
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm leading-6 text-slate-300">
                {status}
              </div>

              {duplicateWarning && (
                <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">
                  Duplicate numbers detected on the board.
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="rounded-3xl border-slate-800 bg-slate-900/90 shadow-2xl">
            <CardHeader>
              <CardTitle className="text-xl">Difficulty Notes</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-slate-300 leading-7">
              <p>Easy: smaller board, more guided clues.</p>
              <p>Medium: wider board with fewer fixed numbers.</p>
              <p>Hard: larger board and sparser clues.</p>
              <p>Later we can compare solver runtime across all 3 levels.</p>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}