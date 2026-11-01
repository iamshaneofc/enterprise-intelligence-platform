import { request } from "./api";
import { ConversationItem } from "@/types";

export const conversationService = {
  async listConversations(workspaceId: string): Promise<ConversationItem[]> {
    try {
      return await request<ConversationItem[]>(
        `/api/v1/workspaces/${workspaceId}/conversations`,
        {
          method: "GET",
        }
      );
    } catch (err: any) {
      console.warn("Backend GET /conversations returned error (known response schema serialization gap):", err?.message);
      return [];
    }
  },

  async getConversation(workspaceId: string, conversationId: string): Promise<ConversationItem> {
    return request<ConversationItem>(
      `/api/v1/workspaces/${workspaceId}/conversations/${conversationId}`,
      {
        method: "GET",
      }
    );
  },

  async deleteConversation(workspaceId: string, conversationId: string): Promise<void> {
    return request<void>(
      `/api/v1/workspaces/${workspaceId}/conversations/${conversationId}`,
      {
        method: "DELETE",
      }
    );
  },
};

