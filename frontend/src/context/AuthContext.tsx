import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { User, Workspace } from "@/types";
import { authService, LoginPayload, RegisterPayload } from "@/services/authService";
import { workspaceService } from "@/services/workspaceService";
import { getAuthToken, setOnUnauthorized } from "@/services/api";

interface AuthContextType {
  user: User | null;
  workspaces: Workspace[];
  currentWorkspace: Workspace | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
  setCurrentWorkspace: (ws: Workspace) => void;
  refreshWorkspaces: () => Promise<void>;
  createWorkspace: (name: string, description?: string) => Promise<Workspace>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [currentWorkspace, setCurrentWorkspaceState] = useState<Workspace | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
    setWorkspaces([]);
    setCurrentWorkspaceState(null);
    localStorage.removeItem("eip_current_workspace_id");
  }, []);

  const setCurrentWorkspace = (ws: Workspace) => {
    setCurrentWorkspaceState(ws);
    try {
      localStorage.setItem("eip_current_workspace_id", ws.id);
    } catch {
      // ignore
    }
  };

  const loadUserData = useCallback(async () => {
    const token = getAuthToken();
    if (!token) {
      setIsLoading(false);
      return;
    }

    try {
      const profile = await authService.getMe();
      setUser(profile);

      const wsList = await workspaceService.listWorkspaces();
      setWorkspaces(wsList);

      const savedWsId = localStorage.getItem("eip_current_workspace_id");
      const matched = wsList.find((w) => w.id === savedWsId);
      if (matched) {
        setCurrentWorkspaceState(matched);
      } else if (wsList.length > 0) {
        setCurrentWorkspaceState(wsList[0]);
        localStorage.setItem("eip_current_workspace_id", wsList[0].id);
      }
    } catch (err) {
      console.error("Failed to load authenticated user:", err);
      logout();
    } finally {
      setIsLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    setOnUnauthorized(() => {
      logout();
    });
    loadUserData();
  }, [loadUserData, logout]);

  const login = async (payload: LoginPayload) => {
    setIsLoading(true);
    try {
      await authService.login(payload);
      await loadUserData();
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (payload: RegisterPayload) => {
    setIsLoading(true);
    try {
      await authService.register(payload);
      // Automatically login after successful registration
      await authService.login({ email: payload.email, password: payload.password });
      await loadUserData();
    } finally {
      setIsLoading(false);
    }
  };

  const refreshWorkspaces = async () => {
    try {
      const wsList = await workspaceService.listWorkspaces();
      setWorkspaces(wsList);
      if (!currentWorkspace && wsList.length > 0) {
        setCurrentWorkspace(wsList[0]);
      }
    } catch (err) {
      console.error("Failed to refresh workspaces:", err);
    }
  };

  const createWorkspace = async (name: string, description?: string) => {
    const newWs = await workspaceService.createWorkspace({ name, description });
    await refreshWorkspaces();
    setCurrentWorkspace(newWs);
    return newWs;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        workspaces,
        currentWorkspace,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        setCurrentWorkspace,
        refreshWorkspaces,
        createWorkspace,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

