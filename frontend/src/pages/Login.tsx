import React, { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Database, AlertCircle, ArrowRight, ShieldCheck } from "lucide-react";

export const Login: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const from = (location.state as any)?.from?.pathname || "/";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await login({ email, password });
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err?.message || "Invalid email or password");
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickFillEmail = (demoEmail: string) => {
    setEmail(demoEmail);
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col justify-center items-center p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl border border-slate-200/80 p-8">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-navy-950 text-blue-500 shadow-md mb-4">
            <Database className="w-6 h-6 text-blue-400" />
          </div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Engineering Intelligence Platform
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Your organization's engineering knowledge, connected and actionable.
          </p>
        </div>

        {error && (
          <div className="mb-6 p-3 rounded-lg bg-rose-50 border border-rose-200 flex items-start gap-2.5 text-xs text-rose-700">
            <AlertCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Work Email"
            type="email"
            placeholder="engineer@enterprise.io"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoFocus
          />

          <Input
            label="Password"
            type="password"
            placeholder="••••••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <Button type="submit" className="w-full mt-2" size="lg" isLoading={isLoading}>
            Sign In to Workspace
          </Button>
        </form>

        {/* Pre-fill email convenience (no hardcoded passwords) */}
        <div className="mt-6 pt-6 border-t border-slate-100">
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 text-center">
            Pre-fill Account Email
          </p>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => handleQuickFillEmail("lead.architect@enterprise.io")}
              className="p-2 text-left rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 transition-colors text-[11px]"
            >
              <span className="font-semibold text-slate-700 block">Lead Architect</span>
              <span className="text-slate-400 text-[10px]">lead.architect@enterprise.io</span>
            </button>
            <button
              type="button"
              onClick={() => handleQuickFillEmail("engineer@enterprise.io")}
              className="p-2 text-left rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 transition-colors text-[11px]"
            >
              <span className="font-semibold text-slate-700 block">Senior Engineer</span>
              <span className="text-slate-400 text-[10px]">engineer@enterprise.io</span>
            </button>
          </div>
        </div>

        <div className="mt-6 text-center text-xs text-slate-600">
          Don't have an account?{" "}
          <Link to="/register" className="font-semibold text-blue-600 hover:text-blue-700">
            Create account
          </Link>
        </div>
      </div>

      <div className="mt-8 flex items-center gap-2 text-xs text-slate-400 font-mono">
        <ShieldCheck className="w-4 h-4 text-emerald-500" />
        <span>Enterprise Zero-Trust Authentication</span>
      </div>
    </div>
  );
};

