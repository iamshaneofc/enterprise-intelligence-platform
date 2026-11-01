import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { documentService } from "@/services/documentService";
import { conversationService } from "@/services/conversationService";
import { agentService } from "@/services/agentService";
import { healthService } from "@/services/healthService";
import { DocumentItem, ConversationItem, AgentRun, SystemHealth } from "@/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  FileText,
  Sparkles,
  Bot,
  Database,
  ArrowRight,
  Upload,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Layers,
  Cpu,
  ShieldCheck,
  Server,
} from "lucide-react";

export const Overview: React.FC = () => {
  const { currentWorkspace, user } = useAuth();
  const navigate = useNavigate();

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [agentRuns, setAgentRuns] = useState<AgentRun[]>([]);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!currentWorkspace) return;

    let isMounted = true;
    setIsLoading(true);

    Promise.all([
      documentService.listDocuments(currentWorkspace.id).catch(() => []),
      conversationService.listConversations(currentWorkspace.id).catch(() => []),
      agentService.listRuns(currentWorkspace.id).catch(() => []),
      healthService.getHealth().catch(() => null),
    ]).then(([docs, convs, runs, healthData]) => {
      if (isMounted) {
        setDocuments(docs);
        setConversations(convs);
        setAgentRuns(runs);
        setHealth(healthData);
        setIsLoading(false);
      }
    });

    return () => {
      isMounted = false;
    };
  }, [currentWorkspace]);

  const completedDocs = documents.filter((d) => d.status === "completed");
  const failedDocs = documents.filter((d) => d.status === "failed");
  const totalChunks = documents.reduce((sum, d) => sum + (d.chunk_count || 0), 0);

  return (
    <div className="space-y-8">
      {/* Welcome Banner */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 md:p-8 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-semibold mb-3 border border-blue-200/60">
            <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
            <span>Workspace: {currentWorkspace?.name || "Active Workspace"}</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Welcome back, {user?.full_name?.split(" ")[0] || "Engineer"}
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Your centralized engineering intelligence workspace. Ingest incident postmortems, query technical knowledge with verified citations, or run autonomous investigation agents.
          </p>
        </div>

        {/* Quick Actions */}
        <div className="flex flex-wrap items-center gap-3">
          <Button
            variant="secondary"
            leftIcon={<Upload className="w-4 h-4 text-slate-500" />}
            onClick={() => navigate("/documents?action=upload")}
          >
            Upload Document
          </Button>
          <Button
            leftIcon={<Sparkles className="w-4 h-4 text-blue-100" />}
            onClick={() => navigate("/chat")}
          >
            Start Investigation
          </Button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card hover>
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                Indexed Documents
              </p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">
                {isLoading ? "—" : completedDocs.length}
              </h3>
              <p className="text-[11px] text-slate-400 mt-1">
                {failedDocs.length > 0 ? `${failedDocs.length} failed` : "All healthy"}
              </p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
              <FileText className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card hover>
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                Embedded Chunks
              </p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">
                {isLoading ? "—" : totalChunks}
              </h3>
              <p className="text-[11px] text-slate-400 mt-1">1536-dim vectors</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
              <Layers className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card hover>
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                AI Investigations
              </p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">
                {isLoading ? "—" : conversations.length}
              </h3>
              <p className="text-[11px] text-slate-400 mt-1">Active chat sessions</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center shrink-0">
              <Sparkles className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card hover>
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                Agent Executions
              </p>
              <h3 className="text-2xl font-bold text-slate-900 mt-1">
                {isLoading ? "—" : agentRuns.length}
              </h3>
              <p className="text-[11px] text-slate-400 mt-1">Multi-step autonomous runs</p>
            </div>
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
              <Bot className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Recent Uploads & Investigations */}
        <div className="lg:col-span-2 space-y-6">
          {/* Recent Documents */}
          <Card>
            <CardHeader className="flex items-center justify-between">
              <div>
                <CardTitle>Recent Technical Documents</CardTitle>
                <CardDescription>Recently ingested postmortems, specs, and runbooks</CardDescription>
              </div>
              <Link to="/documents" className="text-xs text-blue-600 hover:text-blue-700 font-semibold flex items-center gap-1">
                View all <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </CardHeader>
            <CardContent className="p-0">
              {documents.length === 0 ? (
                <div className="p-8 text-center">
                  <FileText className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-xs font-medium text-slate-500">No documents ingested in this workspace yet.</p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-3"
                    onClick={() => navigate("/documents?action=upload")}
                  >
                    Upload first document
                  </Button>
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {documents.slice(0, 4).map((doc) => (
                    <div
                      key={doc.id}
                      onClick={() => navigate(`/documents?doc=${doc.id}`)}
                      className="p-4 flex items-center justify-between hover:bg-slate-50/80 cursor-pointer transition-colors"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-600 flex items-center justify-center font-mono text-[10px] font-bold uppercase shrink-0">
                          {doc.file_type}
                        </div>
                        <div className="min-w-0">
                          <p className="text-xs font-semibold text-slate-900 truncate">{doc.title}</p>
                          <p className="text-[11px] text-slate-500 truncate mt-0.5">
                            {doc.chunk_count} chunks • {(doc.file_size_bytes / 1024).toFixed(1)} KB
                          </p>
                        </div>
                      </div>
                      <Badge
                        variant={
                          doc.status === "completed"
                            ? "success"
                            : doc.status === "processing"
                            ? "primary"
                            : doc.status === "failed"
                            ? "danger"
                            : "warning"
                        }
                        size="sm"
                        dot
                      >
                        {doc.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recent Agent Executions */}
          <Card>
            <CardHeader className="flex items-center justify-between">
              <div>
                <CardTitle>Recent Autonomous Agent Runs</CardTitle>
                <CardDescription>Multi-step technical investigation pipelines</CardDescription>
              </div>
              <Link to="/agents" className="text-xs text-blue-600 hover:text-blue-700 font-semibold flex items-center gap-1">
                View all <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </CardHeader>
            <CardContent className="p-0">
              {agentRuns.length === 0 ? (
                <div className="p-8 text-center">
                  <Bot className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-xs font-medium text-slate-500">No autonomous agent investigations executed yet.</p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-3"
                    onClick={() => navigate("/agents")}
                  >
                    Launch investigation
                  </Button>
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {agentRuns.slice(0, 3).map((run) => (
                    <div
                      key={run.id}
                      onClick={() => navigate(`/agents?run=${run.id}`)}
                      className="p-4 flex items-center justify-between hover:bg-slate-50/80 cursor-pointer transition-colors"
                    >
                      <div className="min-w-0 flex-1 pr-4">
                        <p className="text-xs font-semibold text-slate-900 truncate">{run.task}</p>
                        <div className="flex items-center gap-3 text-[11px] text-slate-500 mt-1">
                          <span>{run.total_steps} steps taken</span>
                          {run.execution_time_ms && (
                            <span>{(run.execution_time_ms / 1000).toFixed(2)}s runtime</span>
                          )}
                        </div>
                      </div>
                      <Badge
                        variant={run.status === "completed" ? "success" : run.status === "failed" ? "danger" : "primary"}
                        size="sm"
                        dot
                      >
                        {run.status}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column (1 Col): System Status & Suggested Investigations */}
        <div className="space-y-6">
          {/* System Health Card */}
          <Card>
            <CardHeader>
              <CardTitle>System & Model Status</CardTitle>
              <CardDescription>Live health and LLM provider connectivity</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3.5">
              <div className="flex items-center justify-between py-1 border-b border-slate-100 text-xs">
                <span className="text-slate-600 flex items-center gap-1.5">
                  <Server className="w-3.5 h-3.5 text-slate-400" /> Backend Core
                </span>
                <span className="font-semibold text-emerald-600 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Healthy (FastAPI)
                </span>
              </div>

              <div className="flex items-center justify-between py-1 border-b border-slate-100 text-xs">
                <span className="text-slate-600 flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-slate-400" /> Vector Database
                </span>
                <span className="font-semibold text-emerald-600 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Connected
                </span>
              </div>

              <div className="flex items-center justify-between py-1 border-b border-slate-100 text-xs">
                <span className="text-slate-600 flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5 text-slate-400" /> Primary LLM
                </span>
                <span className="font-mono text-slate-700 text-[11px]">Claude 3.5 Sonnet</span>
              </div>

              <div className="flex items-center justify-between py-1 text-xs">
                <span className="text-slate-600 flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5 text-slate-400" /> Fallback LLM
                </span>
                <span className="font-mono text-slate-700 text-[11px]">OpenAI GPT-4o</span>
              </div>
            </CardContent>
          </Card>

          {/* Quick Investigation Starters */}
          <Card>
            <CardHeader>
              <CardTitle>Suggested Investigations</CardTitle>
              <CardDescription>Click to launch instant technical inquiry</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {[
                "What caused the database connection pool outage?",
                "Why is API gateway latency increasing?",
                "How does enterprise authentication work?",
              ].map((query, i) => (
                <button
                  key={i}
                  onClick={() => navigate(`/chat?prompt=${encodeURIComponent(query)}`)}
                  className="w-full text-left p-2.5 rounded-lg border border-slate-200 bg-slate-50/60 hover:bg-blue-50/50 hover:border-blue-200 text-xs text-slate-700 transition-colors flex items-center justify-between group"
                >
                  <span className="truncate pr-2 font-medium">{query}</span>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-600 shrink-0" />
                </button>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

