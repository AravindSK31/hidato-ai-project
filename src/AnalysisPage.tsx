import React, { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Loader2,
  RefreshCcw,
  BarChart3,
  Trash2,
  Sparkles,
  X,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

type ResultRecord = {
  puzzle_id: string;
  difficulty: string;
  algorithm: string;
  success: boolean;
  runtime_seconds: number;
  nodes_expanded: number;
  backtracks: number;
  clue_count: number;
  clue_ratio: number;
  board_size: string;
  board_shape: number[];
  clue_pattern: string;
  source: string;
  timestamp: string;
};

type AdversarialPuzzleSummary = {
  puzzle_id: string;
  difficulty: string;
  board_size: string;
  board_shape: number[];
  clue_ratio: number;
  clue_count: number;
  clue_pattern: string;
  seed: number;
  average_hardness: number;
  max_hardness: number;
  failures: number;
  successful_runs: number;
  total_runs: number;
  records: ResultRecord[];
};

type AdversarialResults = {
  summary: {
    config_count: number;
    total_puzzles_evaluated: number;
    total_solver_runs: number;
    total_failures: number;
    total_timeouts: number;
    algorithms: string[];
    timeout_seconds: number;
  };
  all_records: ResultRecord[];
  puzzle_summaries: AdversarialPuzzleSummary[];
  hardest_overall: AdversarialPuzzleSummary[];
  hardest_by_algorithm: Record<string, ResultRecord[]>;
};

function formatSeconds(value: number): string {
  return value.toFixed(6);
}

function formatAlgorithmLabel(algorithm: string): string {
  if (algorithm === "dfs") return "DFS";
  if (algorithm === "dfs_heuristic") return "DFS + Heuristic";
  if (algorithm === "astar") return "A*";
  if (algorithm === "csp") return "CSP";
  if (algorithm === "ga") return "GA";
  return algorithm;
}

function formatDifficultyLabel(difficulty: string): string {
  if (!difficulty) return "-";
  return difficulty.charAt(0).toUpperCase() + difficulty.slice(1).toLowerCase();
}

function formatBoardSizeLabel(boardSize: string): string {
  if (!boardSize) return "-";
  return boardSize.charAt(0).toUpperCase() + boardSize.slice(1).toLowerCase();
}

function formatMetricValue(value: number): string {
  return value < 0 ? "—" : String(value);
}

const woodTooltipStyle = {
  backgroundColor: "rgba(42, 28, 19, 0.96)",
  border: "1px solid rgba(146, 107, 59, 0.45)",
  borderRadius: "14px",
  color: "#f7e7c6",
  boxShadow: "0 10px 30px rgba(0,0,0,0.28)",
};

export default function AnalysisPage() {
  const [results, setResults] = useState<ResultRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("Loading analysis data...");
  const [clearing, setClearing] = useState(false);

  const [algorithmFilter, setAlgorithmFilter] = useState("all");
  const [boardSizeFilter, setBoardSizeFilter] = useState("all");
  const [successFilter, setSuccessFilter] = useState("all");

  const [adversarialLoading, setAdversarialLoading] = useState(false);
  const [adversarialResults, setAdversarialResults] =
    useState<AdversarialResults | null>(null);
  const [showGraphs, setShowGraphs] = useState(false);
  const [showAdversarialModal, setShowAdversarialModal] = useState(false);

  const fetchResults = async () => {
    try {
      setLoading(true);
      setStatus("Loading analysis data...");

      const response = await fetch("http://127.0.0.1:8000/results");
      const data: ResultRecord[] = await response.json();

      const manualOnly = data.filter((item) => item.source === "ui");

      const sorted = [...manualOnly].sort((a, b) =>
        b.timestamp.localeCompare(a.timestamp)
      );

      setResults(sorted);
      setStatus("Analysis data loaded.");
    } catch (error) {
      console.error(error);
      setStatus("Could not load results from backend.");
    } finally {
      setLoading(false);
    }
  };

  const clearHistory = async () => {
    const confirmed = window.confirm(
      "Are you sure you want to clear all stored solver history?"
    );
    if (!confirmed) return;

    try {
      setClearing(true);
      setStatus("Clearing history...");

      const response = await fetch("http://127.0.0.1:8000/results", {
        method: "DELETE",
      });

      const data = await response.json();
      setResults([]);
      setStatus(data.message || "Results history cleared.");
    } catch (error) {
      console.error(error);
      setStatus("Could not clear results history.");
    } finally {
      setClearing(false);
    }
  };

  const runAdversarialSearch = async () => {
    try {
      setAdversarialLoading(true);
      setShowGraphs(false);
      setStatus("Running adversarial search... this can take a little while.");

      const response = await fetch(
        "http://127.0.0.1:8000/run-adversarial?top_k=10&timeout_seconds=15",
        {
          method: "POST",
        }
      );

      const data: AdversarialResults = await response.json();
      setAdversarialResults(data);
      setShowAdversarialModal(true);
      setStatus("Adversarial search completed.");
    } catch (error) {
      console.error(error);
      setStatus("Could not run adversarial search.");
    } finally {
      setAdversarialLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
  }, []);

  const filteredResults = useMemo(() => {
    return results.filter((item) => {
      const algorithmOk =
        algorithmFilter === "all" || item.algorithm === algorithmFilter;
      const boardOk =
        boardSizeFilter === "all" || item.board_size === boardSizeFilter;
      const successOk =
        successFilter === "all" ||
        (successFilter === "success" && item.success) ||
        (successFilter === "failure" && !item.success);

      return algorithmOk && boardOk && successOk;
    });
  }, [results, algorithmFilter, boardSizeFilter, successFilter]);

  const summary = useMemo(() => {
    const total = filteredResults.length;
    const successes = filteredResults.filter((r) => r.success).length;
    const avgRuntime =
      total > 0
        ? filteredResults.reduce((sum, r) => sum + r.runtime_seconds, 0) / total
        : 0;
    const avgNodes =
      total > 0
        ? filteredResults.reduce((sum, r) => sum + r.nodes_expanded, 0) / total
        : 0;
    const avgBacktracks =
      total > 0
        ? filteredResults.reduce((sum, r) => sum + r.backtracks, 0) / total
        : 0;

    return {
      total,
      successes,
      successRate: total > 0 ? (successes / total) * 100 : 0,
      avgRuntime,
      avgNodes,
      avgBacktracks,
    };
  }, [filteredResults]);

  const adversarialFailureChartData = useMemo(() => {
    if (!adversarialResults) return [];

    const counts = new Map<string, number>();

    for (const record of adversarialResults.all_records) {
      if (!record.success) {
        counts.set(record.algorithm, (counts.get(record.algorithm) ?? 0) + 1);
      }
    }

    return Array.from(counts.entries()).map(([algorithm, failures]) => ({
      algorithm: formatAlgorithmLabel(algorithm),
      failures,
    }));
  }, [adversarialResults]);

  const adversarialPatternChartData = useMemo(() => {
    if (!adversarialResults) return [];

    const grouped = new Map<string, { total: number; count: number }>();

    for (const puzzle of adversarialResults.puzzle_summaries) {
      const current = grouped.get(puzzle.clue_pattern) ?? { total: 0, count: 0 };
      current.total += puzzle.average_hardness;
      current.count += 1;
      grouped.set(puzzle.clue_pattern, current);
    }

    return Array.from(grouped.entries()).map(([pattern, values]) => ({
      pattern,
      hardness: Number((values.total / values.count).toFixed(2)),
    }));
  }, [adversarialResults]);

  const adversarialTopPuzzleChartData = useMemo(() => {
    if (!adversarialResults) return [];

    return adversarialResults.hardest_overall.slice(0, 8).map((item) => ({
      puzzle: item.puzzle_id.replace("adv_", "").slice(0, 20),
      hardness: Number(item.average_hardness.toFixed(2)),
    }));
  }, [adversarialResults]);

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#2d1b12_0%,#16110d_45%,#0b0907_100%)] text-white">
      <div className="mx-auto max-w-7xl px-4 py-6 md:px-8 md:py-10">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          <Card className="rounded-[28px] border border-amber-900/30 bg-[linear-gradient(180deg,rgba(64,39,24,0.94)_0%,rgba(32,21,15,0.97)_100%)] shadow-[0_25px_80px_rgba(0,0,0,0.45)]">
            <CardHeader className="border-b border-amber-900/20">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <CardTitle className="text-3xl font-bold tracking-tight text-amber-50">
                    Hidato Analysis Dashboard
                  </CardTitle>
                  <CardDescription className="mt-2 text-base text-amber-100/80">
                    Stored solver runs from manual UI actions.
                  </CardDescription>
                </div>
                <Badge className="rounded-full border border-amber-800 bg-amber-200/90 px-4 py-1 text-amber-950 shadow">
                  <BarChart3 className="mr-2 inline h-4 w-4" />
                  Analysis
                </Badge>
              </div>

              <div className="mt-4 flex flex-wrap gap-3">
                <Button
                  onClick={fetchResults}
                  disabled={loading || clearing || adversarialLoading}
                  className="rounded-full bg-amber-100 text-stone-900 hover:bg-[#f4e7cf]"
                >
                  <RefreshCcw className="mr-2 h-4 w-4" />
                  Refresh Results
                </Button>

                <Button
                  onClick={clearHistory}
                  disabled={loading || clearing || adversarialLoading}
                  className="rounded-full border border-[#7b442e] bg-[linear-gradient(180deg,#8b4b31_0%,#6f3825_100%)] text-white hover:bg-[linear-gradient(180deg,#995337_0%,#7a402a_100%)]"
                >
                  {clearing ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Clearing...
                    </>
                  ) : (
                    <>
                      <Trash2 className="mr-2 h-4 w-4" />
                      Clear History
                    </>
                  )}
                </Button>

                <Button
                  onClick={runAdversarialSearch}
                  disabled={loading || clearing || adversarialLoading}
                  className="rounded-full border border-[#7f5b2a] bg-[linear-gradient(180deg,#9a6f35_0%,#755125_100%)] text-amber-50 hover:bg-[linear-gradient(180deg,#aa7b3a_0%,#815a28_100%)]"
                >
                  {adversarialLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Running Adversarial...
                    </>
                  ) : (
                    <>
                      <Sparkles className="mr-2 h-4 w-4" />
                      Run Adversarial Search
                    </>
                  )}
                </Button>

                <select
                  value={algorithmFilter}
                  onChange={(e) => setAlgorithmFilter(e.target.value)}
                  className="rounded-full border border-amber-700/40 bg-stone-800 px-4 py-2 text-amber-100"
                >
                  <option value="all">All Algorithms</option>
                  <option value="dfs">DFS</option>
                  <option value="dfs_heuristic">DFS + Heuristic</option>
                  <option value="astar">A*</option>
                  <option value="csp">CSP</option>
                  <option value="ga">GA</option>
                </select>

                <select
                  value={boardSizeFilter}
                  onChange={(e) => setBoardSizeFilter(e.target.value)}
                  className="rounded-full border border-amber-700/40 bg-stone-800 px-4 py-2 text-amber-100"
                >
                  <option value="all">All Board Sizes</option>
                  <option value="small">Small</option>
                  <option value="medium">Medium</option>
                  <option value="large">Large</option>
                </select>

                <select
                  value={successFilter}
                  onChange={(e) => setSuccessFilter(e.target.value)}
                  className="rounded-full border border-amber-700/40 bg-stone-800 px-4 py-2 text-amber-100"
                >
                  <option value="all">All Runs</option>
                  <option value="success">Success Only</option>
                  <option value="failure">Failures Only</option>
                </select>
              </div>
            </CardHeader>

            <CardContent className="p-4 md:p-6">
              <div className="rounded-2xl border border-amber-900/20 bg-black/20 p-4 text-sm leading-6 text-amber-100/85">
                {status}
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <Card className="rounded-[24px] border border-amber-900/25 bg-[linear-gradient(180deg,rgba(55,35,24,0.96)_0%,rgba(25,18,14,0.98)_100%)]">
              <CardHeader>
                <CardTitle className="text-lg text-amber-50">Total Runs</CardTitle>
              </CardHeader>
              <CardContent className="text-3xl font-bold text-amber-200">
                {summary.total}
              </CardContent>
            </Card>

            <Card className="rounded-[24px] border border-amber-900/25 bg-[linear-gradient(180deg,rgba(55,35,24,0.96)_0%,rgba(25,18,14,0.98)_100%)]">
              <CardHeader>
                <CardTitle className="text-lg text-amber-50">Success Rate</CardTitle>
              </CardHeader>
              <CardContent className="text-3xl font-bold text-emerald-300">
                {summary.successRate.toFixed(1)}%
              </CardContent>
            </Card>

            <Card className="rounded-[24px] border border-amber-900/25 bg-[linear-gradient(180deg,rgba(55,35,24,0.96)_0%,rgba(25,18,14,0.98)_100%)]">
              <CardHeader>
                <CardTitle className="text-lg text-amber-50">Avg Runtime</CardTitle>
              </CardHeader>
              <CardContent className="text-3xl font-bold text-sky-300">
                {formatSeconds(summary.avgRuntime)}s
              </CardContent>
            </Card>

            <Card className="rounded-[24px] border border-amber-900/25 bg-[linear-gradient(180deg,rgba(55,35,24,0.96)_0%,rgba(25,18,14,0.98)_100%)]">
              <CardHeader>
                <CardTitle className="text-lg text-amber-50">Avg Nodes</CardTitle>
              </CardHeader>
              <CardContent className="text-3xl font-bold text-yellow-300">
                {summary.avgNodes.toFixed(1)}
              </CardContent>
            </Card>

            <Card className="rounded-[24px] border border-amber-900/25 bg-[linear-gradient(180deg,rgba(55,35,24,0.96)_0%,rgba(25,18,14,0.98)_100%)]">
              <CardHeader>
                <CardTitle className="text-lg text-amber-50">Avg Backtracks</CardTitle>
              </CardHeader>
              <CardContent className="text-3xl font-bold text-rose-300">
                {summary.avgBacktracks.toFixed(1)}
              </CardContent>
            </Card>
          </div>

          <Card className="rounded-[28px] border border-amber-900/25 bg-[linear-gradient(180deg,rgba(55,35,24,0.96)_0%,rgba(25,18,14,0.98)_100%)] shadow-[0_18px_50px_rgba(0,0,0,0.35)]">
            <CardHeader>
              <CardTitle className="text-xl text-amber-50">Run History</CardTitle>
              <CardDescription className="text-amber-100/75">
                Only manual solver executions triggered from the main puzzle UI.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center gap-3 text-amber-100/80">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Loading results...
                </div>
              ) : filteredResults.length === 0 ? (
                <div className="text-amber-100/80">No results found.</div>
              ) : (
                <div className="overflow-x-auto rounded-2xl border border-amber-900/20">
                  <table className="min-w-full text-sm">
                    <thead className="bg-amber-900/20 text-amber-100">
                      <tr>
                        <th className="px-4 py-3 text-left">Algorithm</th>
                        <th className="px-4 py-3 text-left">Difficulty</th>
                        <th className="px-4 py-3 text-left">Success</th>
                        <th className="px-4 py-3 text-left">Runtime</th>
                        <th className="px-4 py-3 text-left">Nodes</th>
                        <th className="px-4 py-3 text-left">Backtracks</th>
                        <th className="px-4 py-3 text-left">Board Size</th>
                        <th className="px-4 py-3 text-left">Clues</th>
                        <th className="px-4 py-3 text-left">Pattern</th>
                        <th className="px-4 py-3 text-left">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredResults.map((item) => (
                        <tr
                          key={item.puzzle_id + item.algorithm + item.timestamp}
                          className="border-t border-amber-900/10 text-amber-50/90"
                        >
                          <td className="px-4 py-3">
                            {formatAlgorithmLabel(item.algorithm)}
                          </td>
                          <td className="px-4 py-3">
                            {formatDifficultyLabel(item.difficulty)}
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={
                                item.success ? "text-emerald-300" : "text-rose-300"
                              }
                            >
                              {item.success ? "Success" : "Failure"}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            {formatSeconds(item.runtime_seconds)}s
                          </td>
                          <td className="px-4 py-3">{formatMetricValue(item.nodes_expanded)}</td>
                          <td className="px-4 py-3">{formatMetricValue(item.backtracks)}</td>
                          <td className="px-4 py-3">
                            {formatBoardSizeLabel(item.board_size)}
                          </td>
                          <td className="px-4 py-3">
                            {item.clue_count} ({(item.clue_ratio * 100).toFixed(1)}%)
                          </td>
                          <td className="px-4 py-3">{item.clue_pattern}</td>
                          <td className="px-4 py-3">
                            {new Date(item.timestamp).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {showAdversarialModal && adversarialResults && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-[2px]">
          <div className="max-h-[92vh] w-full max-w-7xl overflow-y-auto rounded-[28px] border border-amber-900/30 bg-[linear-gradient(180deg,rgba(63,39,23,0.98)_0%,rgba(23,16,12,0.99)_100%)] shadow-[0_25px_80px_rgba(0,0,0,0.6)]">
            <div className="sticky top-0 z-10 flex items-center justify-between border-b border-amber-900/20 bg-[linear-gradient(180deg,rgba(94,61,34,0.98)_0%,rgba(31,22,16,0.98)_100%)] px-6 py-4">
              <div>
                <h2 className="text-2xl font-bold text-amber-50">
                  Adversarial Search Results
                </h2>
                <p className="mt-1 text-sm text-amber-100/75">
                  Hardest generated puzzles and solver stress-test summary.
                </p>
              </div>
              <div className="flex items-center gap-3">
                <Button
                  onClick={() => setShowGraphs((prev) => !prev)}
                  className="rounded-full border border-[#7f5b2a] bg-[linear-gradient(180deg,#9a6f35_0%,#755125_100%)] text-amber-50 hover:bg-[linear-gradient(180deg,#aa7b3a_0%,#815a28_100%)]"
                >
                  {showGraphs ? "Hide Graphs" : "Show Graphs"}
                </Button>
                <Button
                  onClick={() => setShowAdversarialModal(false)}
                  className="rounded-full border border-[#7b442e] bg-[linear-gradient(180deg,#8b4b31_0%,#6f3825_100%)] text-white hover:bg-[linear-gradient(180deg,#995337_0%,#7a402a_100%)]"
                >
                  <X className="mr-2 h-4 w-4" />
                  Close
                </Button>
              </div>
            </div>

            <div className="space-y-6 p-6">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                <Card className="rounded-[24px] border border-amber-900/25 bg-[linear-gradient(180deg,rgba(68,44,28,0.96)_0%,rgba(27,18,13,0.98)_100%)]">
                  <CardHeader>
                    <CardTitle className="text-lg text-amber-50">
                      Adversarial Puzzles
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-3xl font-bold text-amber-200">
                    {adversarialResults.summary.total_puzzles_evaluated}
                  </CardContent>
                </Card>

                <Card className="rounded-[24px] border border-amber-900/25 bg-[linear-gradient(180deg,rgba(68,44,28,0.96)_0%,rgba(27,18,13,0.98)_100%)]">
                  <CardHeader>
                    <CardTitle className="text-lg text-amber-50">
                      Solver Runs
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-3xl font-bold text-amber-200">
                    {adversarialResults.summary.total_solver_runs}
                  </CardContent>
                </Card>

                <Card className="rounded-[24px] border border-amber-900/25 bg-[linear-gradient(180deg,rgba(68,44,28,0.96)_0%,rgba(27,18,13,0.98)_100%)]">
                  <CardHeader>
                    <CardTitle className="text-lg text-amber-50">
                      Failures
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-3xl font-bold text-rose-300">
                    {adversarialResults.summary.total_failures}
                  </CardContent>
                </Card>

                <Card className="rounded-[24px] border border-amber-900/25 bg-[linear-gradient(180deg,rgba(68,44,28,0.96)_0%,rgba(27,18,13,0.98)_100%)]">
                  <CardHeader>
                    <CardTitle className="text-lg text-amber-50">
                      Timeouts
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-3xl font-bold text-yellow-300">
                    {adversarialResults.summary.total_timeouts}
                  </CardContent>
                </Card>

                <Card className="rounded-[24px] border border-amber-900/25 bg-[linear-gradient(180deg,rgba(68,44,28,0.96)_0%,rgba(27,18,13,0.98)_100%)]">
                  <CardHeader>
                    <CardTitle className="text-lg text-amber-50">
                      Timeout Budget
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="text-3xl font-bold text-sky-300">
                    {adversarialResults.summary.timeout_seconds}s
                  </CardContent>
                </Card>
              </div>

              <Card className="rounded-[28px] border border-amber-900/25 bg-[linear-gradient(180deg,rgba(55,35,24,0.96)_0%,rgba(25,18,14,0.98)_100%)] shadow-[0_18px_50px_rgba(0,0,0,0.35)]">
                <CardHeader>
                  <CardTitle className="text-xl text-amber-50">
                    Hardest Puzzles Overall
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto rounded-2xl border border-amber-900/20">
                    <table className="min-w-full text-sm">
                      <thead className="bg-amber-900/20 text-amber-100">
                        <tr>
                          <th className="px-4 py-3 text-left">Puzzle ID</th>
                          <th className="px-4 py-3 text-left">Board</th>
                          <th className="px-4 py-3 text-left">Difficulty</th>
                          <th className="px-4 py-3 text-left">Clue Ratio</th>
                          <th className="px-4 py-3 text-left">Pattern</th>
                          <th className="px-4 py-3 text-left">Failures</th>
                          <th className="px-4 py-3 text-left">Avg Hardness</th>
                        </tr>
                      </thead>
                      <tbody>
                        {adversarialResults.hardest_overall.map((item) => (
                          <tr
                            key={item.puzzle_id}
                            className="border-t border-amber-900/10 text-amber-50/90"
                          >
                            <td className="px-4 py-3">{item.puzzle_id}</td>
                            <td className="px-4 py-3">
                              {formatBoardSizeLabel(item.board_size)}
                            </td>
                            <td className="px-4 py-3">
                              {formatDifficultyLabel(item.difficulty)}
                            </td>
                            <td className="px-4 py-3">
                              {item.clue_ratio.toFixed(2)}
                            </td>
                            <td className="px-4 py-3">{item.clue_pattern}</td>
                            <td className="px-4 py-3">{item.failures}</td>
                            <td className="px-4 py-3">
                              {item.average_hardness.toFixed(2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>

              <Card className="rounded-[28px] border border-amber-900/25 bg-[linear-gradient(180deg,rgba(55,35,24,0.96)_0%,rgba(25,18,14,0.98)_100%)] shadow-[0_18px_50px_rgba(0,0,0,0.35)]">
                <CardHeader>
                  <CardTitle className="text-xl text-amber-50">
                    Hardest Cases Per Algorithm
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4 md:grid-cols-2">
                    {Object.entries(adversarialResults.hardest_by_algorithm).map(
                      ([algorithm, records]) => (
                        <Card
                          key={algorithm}
                          className="rounded-[20px] border border-amber-900/20 bg-black/20"
                        >
                          <CardHeader>
                            <CardTitle className="text-base text-amber-50">
                              {formatAlgorithmLabel(algorithm)}
                            </CardTitle>
                          </CardHeader>
                          <CardContent className="space-y-2 text-sm text-amber-100/85">
                            {records.slice(0, 3).map((record) => (
                              <div
                                key={`${record.puzzle_id}-${record.algorithm}`}
                                className="rounded-xl border border-amber-900/20 bg-white/5 p-3"
                              >
                                <div className="font-medium text-amber-50">
                                  {record.puzzle_id}
                                </div>
                                <div>
                                  Success:{" "}
                                  <span
                                    className={
                                      record.success
                                        ? "text-emerald-300"
                                        : "text-rose-300"
                                    }
                                  >
                                    {record.success ? "Yes" : "No"}
                                  </span>
                                </div>
                                <div>
                                  Runtime: {formatSeconds(record.runtime_seconds)}s
                                </div>
                                <div>
                                  Nodes: {formatMetricValue(record.nodes_expanded)}
                                </div>
                                <div>Pattern: {record.clue_pattern}</div>
                              </div>
                            ))}
                          </CardContent>
                        </Card>
                      )
                    )}
                  </div>
                </CardContent>
              </Card>

              {showGraphs && (
                <Card className="rounded-[28px] border border-amber-900/25 bg-[linear-gradient(180deg,rgba(58,39,24,0.96)_0%,rgba(23,18,14,0.98)_100%)] shadow-[0_18px_50px_rgba(0,0,0,0.35)]">
                  <CardHeader>
                    <CardTitle className="text-xl text-amber-50">
                      Adversarial Visual Analysis
                    </CardTitle>
                    <CardDescription className="text-amber-100/75">
                      Clearer labels and muted board-theme styling for the charts.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-10">
                    <div>
                      <h3 className="mb-3 font-semibold text-amber-100">
                        Failures by Algorithm
                      </h3>
                      <div className="h-80 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={adversarialFailureChartData}
                            margin={{ top: 10, right: 20, left: 0, bottom: 10 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(245, 222, 179, 0.10)" />
                            <XAxis
                              dataKey="algorithm"
                              tick={{ fill: "#f3dfb6", fontSize: 12 }}
                              axisLine={{ stroke: "rgba(243,223,182,0.25)" }}
                              tickLine={{ stroke: "rgba(243,223,182,0.25)" }}
                            />
                            <YAxis
                              tick={{ fill: "#f3dfb6", fontSize: 12 }}
                              axisLine={{ stroke: "rgba(243,223,182,0.25)" }}
                              tickLine={{ stroke: "rgba(243,223,182,0.25)" }}
                              label={{
                                value: "Failure Count",
                                angle: -90,
                                position: "insideLeft",
                                fill: "#f3dfb6",
                                style: { textAnchor: "middle" },
                              }}
                            />
                            <Tooltip
                              cursor={{ fill: "rgba(255,255,255,0.03)" }}
                              contentStyle={woodTooltipStyle}
                            />
                            <Bar dataKey="failures" name="Failures" fill="#a56a2d" radius={[8, 8, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    <div>
                      <h3 className="mb-3 font-semibold text-amber-100">
                        Average Hardness by Clue Pattern
                      </h3>
                      <div className="h-80 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={adversarialPatternChartData}
                            margin={{ top: 10, right: 20, left: 0, bottom: 24 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(245, 222, 179, 0.10)" />
                            <XAxis
                              dataKey="pattern"
                              tick={{ fill: "#f3dfb6", fontSize: 11 }}
                              axisLine={{ stroke: "rgba(243,223,182,0.25)" }}
                              tickLine={{ stroke: "rgba(243,223,182,0.25)" }}
                            />
                            <YAxis
                              tick={{ fill: "#f3dfb6", fontSize: 12 }}
                              axisLine={{ stroke: "rgba(243,223,182,0.25)" }}
                              tickLine={{ stroke: "rgba(243,223,182,0.25)" }}
                              label={{
                                value: "Average Hardness",
                                angle: -90,
                                position: "insideLeft",
                                fill: "#f3dfb6",
                                style: { textAnchor: "middle" },
                              }}
                            />
                            <Tooltip
                              cursor={{ fill: "rgba(255,255,255,0.03)" }}
                              contentStyle={woodTooltipStyle}
                            />
                            <Bar dataKey="hardness" name="Avg Hardness" fill="#d0a15d" radius={[8, 8, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    <div>
                      <h3 className="mb-3 font-semibold text-amber-100">
                        Top Hardest Puzzles
                      </h3>
                      <div className="h-80 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={adversarialTopPuzzleChartData}
                            margin={{ top: 10, right: 20, left: 0, bottom: 36 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(245, 222, 179, 0.10)" />
                            <XAxis
                              dataKey="puzzle"
                              angle={-18}
                              textAnchor="end"
                              height={54}
                              tick={{ fill: "#f3dfb6", fontSize: 11 }}
                              axisLine={{ stroke: "rgba(243,223,182,0.25)" }}
                              tickLine={{ stroke: "rgba(243,223,182,0.25)" }}
                            />
                            <YAxis
                              tick={{ fill: "#f3dfb6", fontSize: 12 }}
                              axisLine={{ stroke: "rgba(243,223,182,0.25)" }}
                              tickLine={{ stroke: "rgba(243,223,182,0.25)" }}
                              label={{
                                value: "Hardness Score",
                                angle: -90,
                                position: "insideLeft",
                                fill: "#f3dfb6",
                                style: { textAnchor: "middle" },
                              }}
                            />
                            <Tooltip
                              cursor={{ fill: "rgba(255,255,255,0.03)" }}
                              contentStyle={woodTooltipStyle}
                            />
                            <Bar dataKey="hardness" name="Hardness" fill="#7d8f57" radius={[8, 8, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}