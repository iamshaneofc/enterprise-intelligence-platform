import { request } from "./api";
import { SearchResponse, ChatResponse } from "@/types";

export interface SearchPayload {
  query: string;
  workspace_id: string;
  top_k?: number;
  mode?: "hybrid" | "dense" | "sparse";
}

export interface ChatPayload {
  query: string;
  workspace_id: string;
  conversation_id?: string;
  top_k?: number;
}

export const chatService = {
  async search(workspaceId: string, payload: Omit<SearchPayload, "workspace_id">): Promise<SearchResponse> {
    return request<SearchResponse>(`/api/v1/workspaces/${workspaceId}/search`, {
      method: "POST",
      body: JSON.stringify({
        ...payload,
        workspace_id: workspaceId,
      }),
    });
  },

  async chat(workspaceId: string, payload: Omit<ChatPayload, "workspace_id">): Promise<ChatResponse> {
    return request<ChatResponse>(`/api/v1/workspaces/${workspaceId}/chat`, {
      method: "POST",
      body: JSON.stringify({
        ...payload,
        workspace_id: workspaceId,
      }),
    });
  },
};

