import React, { useState } from "react";
import { evaluationService } from "@/services/evaluationService";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import {
  FileCode,
  ShieldAlert,
  Info,
  Filter,
  Layers,
  Database,
  CheckCircle2,
} from "lucide-react";

export const Evaluation: React.FC = () => {
  const dataset = evaluationService.getBenchmarkDataset();
  const stats = evaluationService.getBenchmarkStats();

  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  const categories = [
    "all",
    ...Array.from(new Set(dataset.map((q) => q.category).filter(Boolean))),
  ];

  const filteredQuestions = dataset.filter((q) => {
    if (selectedCategory === "all") return true;
    return q.category === selectedCategory;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            AI Quality & Evaluation Benchmark
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Golden dataset benchmarks, grounding rules, citation requirements, and abstention test coverage.
          </p>
        </div>

        <Badge variant="warning" size="md" dot>
          Phase 2 Live API Pending
        </Badge>
      </div>

      {/* Honest Backend Endpoint Status Callout */}
      <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 flex items-start gap-3 text-xs text-amber-900">
        <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-semibold text-amber-950">
            Backend Integration Note: Live Batch Evaluation Endpoint
          </p>
          <p className="text-amber-800 leading-relaxed text-[11px]">
            In accordance with the Backend Roadmap, dedicated live batch evaluation endpoints (e.g.{" "}
            <code className="font-mono bg-amber-100/80 px-1 py-0.5 rounded text-amber-900">
              POST /api/v1/evaluation/run
            </code>
            ) are scheduled for Backend Phase 2. To uphold reporting integrity, no fabricated or simulated percentage scores (e.g. Precision@K, citation accuracy) are displayed here.
          </p>
          <p className="text-amber-800 leading-relaxed text-[11px]">
            The benchmark questions below reflect the exact 20 questions from the official golden test fixture (
            <code className="font-mono bg-amber-100/80 px-1 py-0.5 rounded text-amber-900">
              backend/tests/fixtures/golden_evaluation_dataset.jsonl
            </code>
            ) validated by automated integration test suites.
          </p>
        </div>
      </div>

      {/* Actual Factual Dataset Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card hover>
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                Benchmark Questions
              </p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{stats.dataset_size}</h3>
              <p className="text-[11px] text-slate-400 mt-1">Standardized fixture</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
              <Database className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card hover>
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                Evidence-Grounded
              </p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">{stats.grounded_questions}</h3>
              <p className="text-[11px] text-emerald-600 mt-1">Must cite [c_0] sources</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card hover>
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                Negative / Abstentions
              </p>
              <h3 className="text-2xl font-bold text-amber-600 mt-1">{stats.abstention_questions}</h3>
              <p className="text-[11px] text-amber-600 mt-1">Must trigger ABSTAIN</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center shrink-0">
              <ShieldAlert className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card hover>
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                Live Batch Scoring
              </p>
              <h3 className="text-sm font-bold text-slate-500 mt-2">Scheduled Phase 2</h3>
              <p className="text-[11px] text-slate-400 mt-1">No simulated numbers</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-500 flex items-center justify-center shrink-0">
              <Info className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Golden Dataset Explorer */}
      <Card>
        <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <CardTitle>Golden Benchmark Dataset Questions (20 Items)</CardTitle>
            <CardDescription>
              Technical incident queries, architecture specifications, and negative out-of-scope tests
            </CardDescription>
          </div>

          {/* Category Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat === "all" ? "All Categories" : cat}
                </option>
              ))}
            </select>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200/80 text-slate-500 uppercase tracking-wider font-semibold text-[10px]">
                <tr>
                  <th className="px-6 py-3.5 w-16">ID</th>
                  <th className="px-6 py-3.5">Benchmark Question</th>
                  <th className="px-4 py-3.5">Category</th>
                  <th className="px-4 py-3.5">Expected Citations</th>
                  <th className="px-4 py-3.5">Grounding Expectation</th>
                  <th className="px-6 py-3.5 text-right">Dataset Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {filteredQuestions.map((q) => (
                  <tr key={q.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-6 py-3.5 font-mono text-[11px] font-bold text-slate-500">
                      {q.id.toUpperCase()}
                    </td>
                    <td className="px-6 py-3.5 font-medium text-slate-900">{q.question}</td>
                    <td className="px-4 py-3.5">
                      <span className="text-[11px] text-slate-600 bg-slate-100 px-2 py-0.5 rounded font-mono">
                        {q.category}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 font-mono text-[11px] text-blue-600">
                      {q.expected_citations.length > 0
                        ? q.expected_citations.join(", ")
                        : "—"}
                    </td>
                    <td className="px-4 py-3.5">
                      {q.expected_to_abstain ? (
                        <Badge variant="warning" size="sm">
                          Must Abstain
                        </Badge>
                      ) : (
                        <Badge variant="neutral" size="sm">
                          Evidence Grounded
                        </Badge>
                      )}
                    </td>
                    <td className="px-6 py-3.5 text-right font-mono text-[11px] text-slate-400">
                      golden_evaluation_dataset.jsonl
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
