import React, { useState, useEffect } from "react";
import { Link, useLocation, useNavigate, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  FileText,
  Sparkles,
  Bot,
  MessageSquare,
  BarChart3,
  Settings,
  LogOut,
  ChevronDown,
  Plus,
  Search,
  Menu,
  X,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Database,
  Building2,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { healthService } from "@/services/healthService";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

export const AppLayout: React.FC = () => {
  const { user, workspaces, currentWorkspace, setCurrentWorkspace, createWorkspace, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isWorkspaceMenuOpen, setIsWorkspaceMenuOpen] = useState(false);
  const [isCreateWsModalOpen, setIsCreateWsModalOpen] = useState(false);
  const [newWsName, setNewWsName] = useState("");
  const [isCreatingWs, setIsCreatingWs] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [systemStatus, setSystemStatus] = useState<"ok" | "degraded" | "checking">("checking");
  const [globalSearchQuery, setGlobalSearchQuery] = useState("");

  useEffect(() => {
    // Check backend health on load
    healthService
      .getReadiness()
      .then(() => setSystemStatus("ok"))
      .catch(() => setSystemStatus("degraded"));
  }, []);

  const navItems = [
    { name: "Overview", path: "/", icon: LayoutDashboard },
    { name: "Knowledge Base", path: "/documents", icon: FileText },
    { name: "AI Investigation", path: "/chat", icon: Sparkles },
    { name: "Agent Runs", path: "/agents", icon: Bot },
    { name: "Conversations", path: "/conversations", icon: MessageSquare },
    { name: "Evaluation", path: "/evaluation", icon: BarChart3 },
    { name: "Settings", path: "/settings", icon: Settings },
  ];

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWsName.trim()) return;
    setIsCreatingWs(true);
    try {
      await createWorkspace(newWsName.trim());
      setNewWsName("");
      setIsCreateWsModalOpen(false);
    } catch (err) {
      console.error("Failed to create workspace:", err);
    } finally {
      setIsCreatingWs(false);
    }
  };

  const handleGlobalSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (globalSearchQuery.trim()) {
      navigate(`/documents?search=${encodeURIComponent(globalSearchQuery.trim())}`);
      setGlobalSearchQuery("");
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col md:flex-row font-sans">
      {/* Mobile Backdrop */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-slate-950/60 z-40 md:hidden backdrop-blur-xs"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Deep Navy Sidebar */}
      <aside
        className={`fixed md:sticky top-0 inset-y-0 left-0 z-50 w-64 bg-navy-950 text-slate-300 flex flex-col border-r border-navy-800 transition-transform duration-200 ease-in-out md:translate-x-0 ${
          isSidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* App Brand Header */}
        <div className="h-16 flex items-center justify-between px-5 border-b border-navy-800/80 bg-navy-950/60">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold shadow-sm shadow-blue-500/20">
              <Database className="w-4 h-4 text-blue-100" />
            </div>
            <div>
              <span className="text-sm font-bold text-white tracking-tight leading-none block">
                Engineering Intel
              </span>
              <span className="text-[10px] text-blue-400 font-mono tracking-wider uppercase block mt-0.5">
                Enterprise Platform
              </span>
            </div>
          </Link>
          <button
            onClick={() => setIsSidebarOpen(false)}
            className="md:hidden text-slate-400 hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Workspace Switcher */}
        <div className="px-3 py-3 border-b border-navy-800/60">
          <div className="relative">
            <button
              onClick={() => setIsWorkspaceMenuOpen(!isWorkspaceMenuOpen)}
              className="w-full flex items-center justify-between p-2 rounded-lg bg-navy-900/90 hover:bg-navy-800/90 text-left transition-colors border border-navy-800 text-xs"
            >
              <div className="flex items-center gap-2 truncate">
                <Building2 className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                <span className="font-semibold text-slate-200 truncate">
                  {currentWorkspace?.name || "Select Workspace"}
                </span>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0 ml-1" />
            </button>

            {isWorkspaceMenuOpen && (
              <div
                className="absolute top-full left-0 right-0 mt-1 z-30 bg-navy-900 border border-navy-800 rounded-lg shadow-xl py-1 overflow-hidden"
                onMouseLeave={() => setIsWorkspaceMenuOpen(false)}
              >
                <div className="px-3 py-1.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                  Workspaces
                </div>
                <div className="max-h-48 overflow-y-auto">
                  {workspaces.map((ws) => (
                    <button
                      key={ws.id}
                      onClick={() => {
                        setCurrentWorkspace(ws);
                        setIsWorkspaceMenuOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 text-xs flex items-center justify-between hover:bg-navy-800 transition-colors ${
                        currentWorkspace?.id === ws.id
                          ? "bg-blue-600/20 text-blue-400 font-semibold"
                          : "text-slate-300"
                      }`}
                    >
                      <span className="truncate">{ws.name}</span>
                      {currentWorkspace?.id === ws.id && (
                        <CheckCircle2 className="w-3 h-3 text-blue-400 shrink-0" />
                      )}
                    </button>
                  ))}
                </div>
                <div className="p-1 border-t border-navy-800 mt-1">
                  <button
                    onClick={() => {
                      setIsWorkspaceMenuOpen(false);
                      setIsCreateWsModalOpen(true);
                    }}
                    className="w-full flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-blue-400 hover:bg-navy-800 rounded transition-colors font-medium"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Create Workspace</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.path === "/"
                ? location.pathname === "/"
                : location.pathname.startsWith(item.path);

            return (
              <Link
                key={item.name}
                to={item.path}
                onClick={() => setIsSidebarOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? "bg-blue-600 text-white font-semibold shadow-sm shadow-blue-600/30"
                    : "text-slate-400 hover:text-slate-200 hover:bg-navy-900"
                }`}
              >
                <Icon className={`w-4 h-4 shrink-0 ${isActive ? "text-white" : "text-slate-400"}`} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>

        {/* User Profile / Status Footer */}
        <div className="p-3 border-t border-navy-800/80 bg-navy-950/80">
          <div className="flex items-center justify-between p-2 rounded-lg bg-navy-900/60 border border-navy-800/60">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-7 h-7 rounded-full bg-blue-700 text-white flex items-center justify-center font-bold text-xs uppercase shrink-0">
                {user?.full_name?.charAt(0) || "U"}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-slate-200 truncate leading-none">
                  {user?.full_name || "Engineer"}
                </p>
                <p className="text-[10px] text-slate-400 truncate mt-0.5 leading-none">
                  {user?.role || "engineer"}
                </p>
              </div>
            </div>
            <button
              onClick={logout}
              title="Sign Out"
              className="text-slate-400 hover:text-rose-400 p-1 rounded hover:bg-navy-800 transition-colors shrink-0"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto">
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-slate-200/80 px-4 md:px-8 flex items-center justify-between shrink-0 sticky top-0 z-30">
          <div className="flex items-center gap-3 flex-1 max-w-xl">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="md:hidden text-slate-600 hover:text-slate-900 p-1 rounded-md hover:bg-slate-100"
            >
              <Menu className="w-5 h-5" />
            </button>

            {/* Global Search Bar */}
            <form onSubmit={handleGlobalSearch} className="w-full relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search across documents, incidents, runbooks..."
                value={globalSearchQuery}
                onChange={(e) => setGlobalSearchQuery(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-4 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all"
              />
            </form>
          </div>

          <div className="flex items-center gap-4 ml-4">
            {/* Health Status Indicator */}
            <div
              className={`hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border ${
                systemStatus === "ok"
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : systemStatus === "degraded"
                  ? "bg-rose-50 text-rose-700 border-rose-200"
                  : "bg-slate-50 text-slate-600 border-slate-200"
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  systemStatus === "ok"
                    ? "bg-emerald-500"
                    : systemStatus === "degraded"
                    ? "bg-rose-500"
                    : "bg-slate-400"
                }`}
              />
              <span>{systemStatus === "ok" ? "Backend Connected" : "Connecting..."}</span>
            </div>

            {/* User Dropdown */}
            <div className="relative">
              <button
                onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                className="flex items-center gap-2 hover:bg-slate-100 p-1.5 rounded-lg transition-colors"
              >
                <div className="w-7 h-7 rounded-full bg-slate-800 text-white font-semibold text-xs flex items-center justify-center">
                  {user?.full_name?.charAt(0) || "U"}
                </div>
                <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
              </button>

              {isUserMenuOpen && (
                <div
                  className="absolute right-0 mt-1 w-56 bg-white border border-slate-200 rounded-xl shadow-lg py-1 z-40"
                  onMouseLeave={() => setIsUserMenuOpen(false)}
                >
                  <div className="px-4 py-2 border-b border-slate-100">
                    <p className="text-xs font-semibold text-slate-900">{user?.full_name}</p>
                    <p className="text-[11px] text-slate-500 truncate">{user?.email}</p>
                  </div>
                  <Link
                    to="/settings"
                    onClick={() => setIsUserMenuOpen(false)}
                    className="flex items-center gap-2 px-4 py-2 text-xs text-slate-700 hover:bg-slate-50"
                  >
                    <Settings className="w-3.5 h-3.5" />
                    <span>Workspace Settings</span>
                  </Link>
                  <button
                    onClick={() => {
                      setIsUserMenuOpen(false);
                      logout();
                    }}
                    className="w-full flex items-center gap-2 px-4 py-2 text-xs text-rose-600 hover:bg-rose-50 border-t border-slate-100 text-left"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>Sign Out</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page Content Outlet */}
        <main className="flex-1 p-4 md:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>

      {/* Create Workspace Modal */}
      <Modal
        isOpen={isCreateWsModalOpen}
        onClose={() => setIsCreateWsModalOpen(false)}
        title="Create New Engineering Workspace"
        description="Organize technical documents, runbooks, and investigations into an isolated tenant."
      >
        <form onSubmit={handleCreateWorkspace} className="space-y-4">
          <Input
            label="Workspace Name"
            placeholder="e.g. Core Infrastructure & SRE"
            value={newWsName}
            onChange={(e) => setNewWsName(e.target.value)}
            required
            autoFocus
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsCreateWsModalOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" isLoading={isCreatingWs}>
              Create Workspace
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
