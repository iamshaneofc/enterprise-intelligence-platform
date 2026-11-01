import { request } from "./api";
import { AgentRun } from "@/types";

export interface InvestigatePayload {
  task: string;
  conversation_id?: string;
  max_steps?: number;
}

export const agentService = {
  async triggerInvestigation(workspaceId: string, payload: InvestigatePayload): Promise<AgentRun> {
    return request<AgentRun>(
      `/api/v1/workspaces/${workspaceId}/agent/investigate`,
      {
        method: "POST",
        body: JSON.stringify({
          ...payload,
          workspace_id: workspaceId,
        }),
      }
    );
  },

  async listRuns(workspaceId: string): Promise<AgentRun[]> {
    return request<AgentRun[]>(
      `/api/v1/workspaces/${workspaceId}/agent/runs`,
      {
        method: "GET",
      }
    );
  },

  async getRun(workspaceId: string, runId: string): Promise<AgentRun> {
    return request<AgentRun>(
      `/api/v1/workspaces/${workspaceId}/agent/runs/${runId}`,
      {
        method: "GET",
      }
    );
  },
};

