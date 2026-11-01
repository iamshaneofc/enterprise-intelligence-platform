import { request } from "./api";
import { ConversationItem } from "@/types";

export const conversationService = {
  async listConversations(workspaceId: string): Promise<ConversationItem[]> {
    return request<ConversationItem[]>(
      `/api/v1/workspaces/${workspaceId}/conversations`,
      {
        method: "GET",
      }
    );
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

