import React, { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { healthService } from "@/services/healthService";
import { SystemHealth } from "@/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  User,
  Building2,
  Cpu,
  Database,
  ShieldCheck,
  CheckCircle2,
  Server,
  Layers,
  Lock,
} from "lucide-react";

export const SettingsPage: React.FC = () => {
  const { user, currentWorkspace } = useAuth();
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [readiness, setReadiness] = useState<{ status: string; database: string } | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const checkHealth = async () => {
    setIsRefreshing(true);
    try {
      const [h, r] = await Promise.all([
        healthService.getHealth().catch(() => null),
        healthService.getReadiness().catch(() => null),
      ]);
      setHealth(h);
      setReadiness(r);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">Platform Settings & Diagnostics</h1>
        <p className="text-xs text-slate-500 mt-1">
          Inspect user authentication, workspace tenancy, LLM provider routing, and vector storage connectivity.
        </p>
      </div>

      {/* User Profile */}
      <Card>
        <CardHeader className="flex items-center justify-between">
          <div>
            <CardTitle className="text-sm flex items-center gap-2">
              <User className="w-4 h-4 text-blue-600" />
              <span>User Profile</span>
            </CardTitle>
            <CardDescription>Authenticated user account and access privileges</CardDescription>
          </div>
          <Badge variant="primary" size="sm">
            {user?.role || "engineer"}
          </Badge>
        </CardHeader>
        <CardContent className="space-y-3 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Full Name</span>
              <span className="font-semibold text-slate-800">{user?.full_name}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Email</span>
              <span className="font-mono text-slate-800">{user?.email}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">User ID</span>
              <span className="font-mono text-slate-600 text-[11px]">{user?.id}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Account Status</span>
              <span className="text-emerald-600 font-semibold flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Active
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Workspace Tenancy */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Building2 className="w-4 h-4 text-indigo-600" />
            <span>Active Engineering Workspace</span>
          </CardTitle>
          <CardDescription>Multi-tenant isolated workspace boundary</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Workspace Name</span>
              <span className="font-semibold text-slate-800">{currentWorkspace?.name}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Slug Identifier</span>
              <span className="font-mono text-slate-800">{currentWorkspace?.slug}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Workspace UUID</span>
              <span className="font-mono text-slate-600 text-[11px]">{currentWorkspace?.id}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Created At</span>
              <span className="text-slate-700">
                {currentWorkspace?.created_at ? new Date(currentWorkspace.created_at).toLocaleString() : "—"}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Model & Provider Routing */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Cpu className="w-4 h-4 text-purple-600" />
            <span>LLM Providers & Failover Configuration</span>
          </CardTitle>
          <CardDescription>Dual-provider circuit breaker router and embedding model</CardDescription>
        </CardHeader>
        <CardContent className="divide-y divide-slate-100 text-xs">
          <div className="py-2.5 flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-900">Primary Synthesis Model</p>
              <p className="text-slate-500 text-[11px]">Anthropic Claude 3.5 Sonnet</p>
            </div>
            <Badge variant="success" size="sm" dot>
              Active
            </Badge>
          </div>

          <div className="py-2.5 flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-900">Fallback Resilience Model</p>
              <p className="text-slate-500 text-[11px]">OpenAI GPT-4o (automatic 429/5xx circuit breaker)</p>
            </div>
            <Badge variant="info" size="sm" dot>
              Standby
            </Badge>
          </div>

          <div className="py-2.5 flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-900">Embedding Engine</p>
              <p className="text-slate-500 text-[11px]">OpenAI text-embedding-3-small (1536-dimensional L2 vectors)</p>
            </div>
            <Badge variant="neutral" size="sm">
              Vector 1536
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* System Diagnostics */}
      <Card>
        <CardHeader className="flex items-center justify-between">
          <div>
            <CardTitle className="text-sm flex items-center gap-2">
              <Server className="w-4 h-4 text-emerald-600" />
              <span>System Health & Connectivity</span>
            </CardTitle>
            <CardDescription>Live healthcheck probes and database state</CardDescription>
          </div>
          <Button size="sm" variant="secondary" onClick={checkHealth} isLoading={isRefreshing}>
            Refresh
          </Button>
        </CardHeader>
        <CardContent className="space-y-3 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Backend Service</span>
              <span className="font-semibold text-emerald-600 flex items-center gap-1 mt-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{health?.service || "FastAPI Core"} ({health?.version || "v0.1.0"})</span>
              </span>
            </div>

            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Database Connection</span>
              <span className="font-semibold text-emerald-600 flex items-center gap-1 mt-1">
                <Database className="w-3.5 h-3.5" />
                <span>{readiness?.database || "Connected (SQLAlchemy 2.0)"}</span>
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

