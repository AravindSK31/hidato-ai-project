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
import { Loader2, RefreshCcw, BarChart3 } from "lucide-react";

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

function formatSeconds(value: number): string {
  return value.toFixed(6);
}

export default function AnalysisPage() {
  const [results, setResults] = useState<ResultRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("Loading analysis data...");

  const [algorithmFilter, setAlgorithmFilter] = useState("all");
  const [boardSizeFilter, setBoardSizeFilter] = useState("all");
  const [successFilter, setSuccessFilter] = useState("all");

  const fetchResults = async () => {
    try {
      setLoading(true);
      setStatus("Loading analysis data...");

      const response = await fetch("http://127.0.0.1:8000/results");
      const data: ResultRecord[] = await response.json();

      const sorted = [...data].sort((a, b) =>
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

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#2d1b12_0%,#16110d_45%,#0b0907_100%)] text-white">
      <div className="max-w-7xl mx-auto px-4 py-6 md:px-8 md:py-10">
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
                  <CardDescription className="mt-2 text-amber-100/80 text-base">
                    Stored solver runs across puzzles and algorithms.
                  </CardDescription>
                </div>
                <Badge className="rounded-full border border-amber-800 bg-amber-200/90 px-4 py-1 text-amber-950 shadow">
                  <BarChart3 className="mr-2 h-4 w-4 inline" />
                  Analysis
                </Badge>
              </div>

              <div className="mt-4 flex flex-wrap gap-3">
                <Button
                  onClick={fetchResults}
                  className="rounded-full bg-amber-100 text-stone-900 hover:bg-white"
                >
                  <RefreshCcw className="mr-2 h-4 w-4" />
                  Refresh Results
                </Button>

                <select
                  value={algorithmFilter}
                  onChange={(e) => setAlgorithmFilter(e.target.value)}
                  className="rounded-full bg-stone-800 px-4 py-2 text-amber-100 border border-amber-700/40"
                >
                  <option value="all">All Algorithms</option>
                  <option value="dfs">DFS</option>
                  <option value="csp">CSP</option>
                </select>

                <select
                  value={boardSizeFilter}
                  onChange={(e) => setBoardSizeFilter(e.target.value)}
                  className="rounded-full bg-stone-800 px-4 py-2 text-amber-100 border border-amber-700/40"
                >
                  <option value="all">All Board Sizes</option>
                  <option value="small">Small</option>
                  <option value="medium">Medium</option>
                  <option value="large">Large</option>
                </select>

                <select
                  value={successFilter}
                  onChange={(e) => setSuccessFilter(e.target.value)}
                  className="rounded-full bg-stone-800 px-4 py-2 text-amber-100 border border-amber-700/40"
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
                Every stored solver execution from the UI and future batch runs.
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
                        <th className="px-4 py-3 text-left">Success</th>
                        <th className="px-4 py-3 text-left">Runtime</th>
                        <th className="px-4 py-3 text-left">Nodes</th>
                        <th className="px-4 py-3 text-left">Backtracks</th>
                        <th className="px-4 py-3 text-left">Board</th>
                        <th className="px-4 py-3 text-left">Clues</th>
                        <th className="px-4 py-3 text-left">Pattern</th>
                        <th className="px-4 py-3 text-left">Source</th>
                        <th className="px-4 py-3 text-left">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredResults.map((item) => (
                        <tr
                          key={item.puzzle_id + item.algorithm + item.timestamp}
                          className="border-t border-amber-900/10 text-amber-50/90"
                        >
                          <td className="px-4 py-3 uppercase">{item.algorithm}</td>
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
                          <td className="px-4 py-3">{item.nodes_expanded}</td>
                          <td className="px-4 py-3">{item.backtracks}</td>
                          <td className="px-4 py-3">{item.board_size}</td>
                          <td className="px-4 py-3">
                            {item.clue_count} ({(item.clue_ratio * 100).toFixed(1)}%)
                          </td>
                          <td className="px-4 py-3">{item.clue_pattern}</td>
                          <td className="px-4 py-3">{item.source}</td>
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
    </div>
  );
}