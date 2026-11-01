import { request } from "./api";
import { Workspace } from "@/types";

export interface CreateWorkspacePayload {
  name: string;
  slug?: string;
  description?: string;
}

export const workspaceService = {
  async listWorkspaces(): Promise<Workspace[]> {
    return request<Workspace[]>("/api/v1/workspaces", {
      method: "GET",
    });
  },

  async createWorkspace(payload: CreateWorkspacePayload): Promise<Workspace> {
    return request<Workspace>("/api/v1/workspaces", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getWorkspace(workspaceId: string): Promise<Workspace> {
    return request<Workspace>(`/api/v1/workspaces/${workspaceId}`, {
      method: "GET",
    });
  },
};

