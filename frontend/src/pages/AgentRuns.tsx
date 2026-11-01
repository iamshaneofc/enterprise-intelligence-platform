import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { agentService } from "@/services/agentService";
import { AgentRun } from "@/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import {
  Bot,
  Plus,
  Clock,
  Play,
  CheckCircle2,
  AlertCircle,
  FileText,
  Search,
  Code,
  ChevronDown,
  ChevronRight,
  ShieldAlert,
  Sparkles,
} from "lucide-react";

export const AgentRuns: React.FC = () => {
  const { currentWorkspace } = useAuth();
  const [searchParams] = useSearchParams();

  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<AgentRun | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // New Investigation Modal
  const [isNewRunModalOpen, setIsNewRunModalOpen] = useState(false);
  const [taskPrompt, setTaskPrompt] = useState("");
  const [maxSteps, setMaxSteps] = useState(5);
  const [isLaunching, setIsLaunching] = useState(false);
  const [launchError, setLaunchError] = useState<string | null>(null);

  // Expanded tool cards in execution view
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({});

  const loadRuns = async () => {
    if (!currentWorkspace) return;
    setIsLoading(true);
    try {
      const data = await agentService.listRuns(currentWorkspace.id);
      setRuns(data);

      const targetRunId = searchParams.get("run");
      if (targetRunId) {
        const found = data.find((r) => r.id === targetRunId);
        if (found) setSelectedRun(found);
      } else if (data.length > 0 && !selectedRun) {
        setSelectedRun(data[0]);
      }
    } catch (err) {
      console.error("Failed to load agent runs:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, [currentWorkspace]);

  const handleLaunchInvestigation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskPrompt.trim() || !currentWorkspace) return;

    setIsLaunching(true);
    setLaunchError(null);

    try {
      const newRun = await agentService.triggerInvestigation(currentWorkspace.id, {
        task: taskPrompt.trim(),
        max_steps: maxSteps,
      });

      setTaskPrompt("");
      setIsNewRunModalOpen(false);
      await loadRuns();
      setSelectedRun(newRun);
    } catch (err: any) {
      setLaunchError(err?.message || "Failed to launch agent investigation");
    } finally {
      setIsLaunching(false);
    }
  };

  const toggleStep = (stepNumber: number) => {
    setExpandedSteps((prev) => ({
      ...prev,
      [stepNumber]: !prev[stepNumber],
    }));
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Autonomous Agent Runs</h1>
          <p className="text-xs text-slate-500 mt-1">
            Controlled multi-tool reasoning loops (Search, Analysis, Report Generation) with complete execution traces.
          </p>
        </div>
        <Button
          leftIcon={<Play className="w-4 h-4" />}
          onClick={() => {
            setLaunchError(null);
            setIsNewRunModalOpen(true);
          }}
        >
          New Investigation
        </Button>
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (1 Col): Agent Run History */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="p-4">
              <CardTitle className="text-sm">Investigation Runs</CardTitle>
              <CardDescription>Select a run to inspect its execution trace</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {isLoading ? (
                <div className="p-8 text-center text-xs text-slate-400">Loading runs...</div>
              ) : runs.length === 0 ? (
                <div className="p-8 text-center">
                  <Bot className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-xs font-semibold text-slate-700">No agent runs executed yet</p>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Launch a multi-step investigation to start.
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-slate-100 max-h-[600px] overflow-y-auto">
                  {runs.map((run) => (
                    <div
                      key={run.id}
                      onClick={() => setSelectedRun(run)}
                      className={`p-3.5 cursor-pointer transition-colors text-xs ${
                        selectedRun?.id === run.id
                          ? "bg-blue-50/80 border-l-4 border-blue-600"
                          : "hover:bg-slate-50"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <Badge
                          variant={
                            run.status === "completed"
                              ? "success"
                              : run.status === "failed"
                              ? "danger"
                              : "primary"
                          }
                          size="sm"
                          dot
                        >
                          {run.status}
                        </Badge>
                        <span className="text-[10px] text-slate-400 font-mono">
                          {new Date(run.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </div>
                      <p className="font-semibold text-slate-900 line-clamp-2">{run.task}</p>
                      <div className="flex items-center gap-3 text-[10px] text-slate-500 mt-2 font-mono">
                        <span>{run.total_steps} steps</span>
                        {run.execution_time_ms && (
                          <span>{(run.execution_time_ms / 1000).toFixed(2)}s</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column (2 Cols): Selected Run Details & Execution Traces */}
        <div className="lg:col-span-2 space-y-6">
          {selectedRun ? (
            <>
              {/* Header Card */}
              <Card>
                <CardHeader className="p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <Badge
                          variant={
                            selectedRun.status === "completed"
                              ? "success"
                              : selectedRun.status === "failed"
                              ? "danger"
                              : "primary"
                          }
                          size="sm"
                          dot
                        >
                          {selectedRun.status}
                        </Badge>
                        <span className="text-xs font-mono text-slate-400">
                          ID: {selectedRun.id.slice(0, 8)}...
                        </span>
                      </div>
                      <h2 className="text-base font-bold text-slate-900">{selectedRun.task}</h2>
                    </div>

                    <div className="text-right text-xs text-slate-500 font-mono shrink-0">
                      <div>Steps: {selectedRun.total_steps}</div>
                      {selectedRun.execution_time_ms && (
                        <div>Duration: {(selectedRun.execution_time_ms / 1000).toFixed(2)}s</div>
                      )}
                    </div>
                  </div>
                </CardHeader>
              </Card>

              {/* Step-by-Step Tool Execution Timeline */}
              <Card>
                <CardHeader className="p-4 border-b border-slate-100">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Clock className="w-4 h-4 text-blue-600" />
                    <span>Agent Execution Traces</span>
                  </CardTitle>
                  <CardDescription>
                    Sequential tool calls dispatched during autonomous reasoning loop
                  </CardDescription>
                </CardHeader>
                <CardContent className="p-4 space-y-3">
                  {selectedRun.tool_executions.length === 0 ? (
                    <p className="text-xs text-slate-400 py-4 text-center">
                      No tool executions recorded for this run.
                    </p>
                  ) : (
                    selectedRun.tool_executions.map((step) => {
                      const isExpanded = !!expandedSteps[step.step_number];

                      return (
                        <div
                          key={step.id}
                          className="rounded-xl border border-slate-200 bg-white overflow-hidden text-xs shadow-2xs"
                        >
                          <div
                            onClick={() => toggleStep(step.step_number)}
                            className="p-3 bg-slate-50/70 hover:bg-slate-100/70 cursor-pointer flex items-center justify-between transition-colors"
                          >
                            <div className="flex items-center gap-3">
                              <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 font-mono font-bold flex items-center justify-center text-[10px] shrink-0">
                                #{step.step_number}
                              </span>
                              <div>
                                <span className="font-mono font-semibold text-slate-900">
                                  {step.tool_name}
                                </span>
                                <span className="text-slate-400 text-[10px] ml-2 font-mono">
                                  {step.execution_time_ms}ms
                                </span>
                              </div>
                            </div>

                            <div className="flex items-center gap-2">
                              <Badge
                                variant={step.status === "success" ? "success" : "danger"}
                                size="sm"
                              >
                                {step.status}
                              </Badge>
                              {isExpanded ? (
                                <ChevronDown className="w-4 h-4 text-slate-400" />
                              ) : (
                                <ChevronRight className="w-4 h-4 text-slate-400" />
                              )}
                            </div>
                          </div>

                          {/* Expanded JSON Inspector */}
                          {isExpanded && (
                            <div className="p-4 space-y-3 bg-white border-t border-slate-100 font-mono text-[11px]">
                              <div>
                                <span className="text-slate-400 text-[10px] uppercase font-bold block mb-1">
                                  Tool Input:
                                </span>
                                <pre className="bg-slate-900 text-slate-100 p-3 rounded-lg overflow-x-auto leading-normal">
                                  {JSON.stringify(step.tool_input, null, 2)}
                                </pre>
                              </div>

                              <div>
                                <span className="text-slate-400 text-[10px] uppercase font-bold block mb-1">
                                  Tool Output:
                                </span>
                                <pre className="bg-slate-900 text-emerald-400 p-3 rounded-lg overflow-x-auto leading-normal">
                                  {JSON.stringify(step.tool_output, null, 2)}
                                </pre>
                              </div>

                              {step.error_message && (
                                <div className="p-2.5 rounded-lg bg-rose-50 text-rose-700 border border-rose-200">
                                  Error: {step.error_message}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })
                  )}
                </CardContent>
              </Card>

              {/* Formatted Final Investigation Report */}
              {selectedRun.final_output && (
                <Card>
                  <CardHeader className="p-4 border-b border-slate-100">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <FileText className="w-4 h-4 text-emerald-600" />
                      <span>Synthesized Investigation Report</span>
                    </CardTitle>
                    <CardDescription>
                      Structured findings, evidence, and actionable recommendations
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-6 bg-slate-50/40">
                    <MarkdownRenderer content={selectedRun.final_output} />
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            <div className="h-64 flex flex-col items-center justify-center bg-white rounded-xl border border-slate-200 text-slate-400 text-xs">
              <Bot className="w-8 h-8 text-slate-300 mb-2" />
              <span>Select an investigation run from the left panel to inspect details.</span>
            </div>
          )}
        </div>
      </div>

      {/* New Investigation Modal */}
      <Modal
        isOpen={isNewRunModalOpen}
        onClose={() => {
          if (!isLaunching) setIsNewRunModalOpen(false);
        }}
        title="Launch Autonomous Technical Investigation"
        description="The agent will independently plan, search documents, inspect evidence, and synthesize an incident report."
      >
        <form onSubmit={handleLaunchInvestigation} className="space-y-4">
          {launchError && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 flex items-start gap-2 text-xs text-rose-700">
              <AlertCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
              <span>{launchError}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Investigation Objective
            </label>
            <textarea
              rows={4}
              placeholder="e.g. Investigate the root cause, timeline, and mitigation steps for the PostgreSQL connection pool exhaustion incident."
              value={taskPrompt}
              onChange={(e) => setTaskPrompt(e.target.value)}
              required
              className="w-full rounded-lg border border-slate-300 bg-white p-3 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <label className="font-semibold text-slate-700">Max Reasoning Steps</label>
              <span className="font-mono text-slate-500 font-bold">{maxSteps} steps</span>
            </div>
            <input
              type="range"
              min={1}
              max={10}
              value={maxSteps}
              onChange={(e) => setMaxSteps(Number(e.target.value))}
              className="w-full accent-blue-600"
            />
            <p className="text-[11px] text-slate-400">
              Upper bound on tool execution cycles to prevent runaway execution.
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsNewRunModalOpen(false)}
              disabled={isLaunching}
            >
              Cancel
            </Button>
            <Button type="submit" isLoading={isLaunching} disabled={!taskPrompt.trim()}>
              Launch Agent
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

