import { request } from "./api";
import { SystemHealth } from "@/types";

export const healthService = {
  async getHealth(): Promise<SystemHealth> {
    return request<SystemHealth>("/health", {
      method: "GET",
    });
  },

  async getReadiness(): Promise<{ status: string; database: string; timestamp: string }> {
    return request<{ status: string; database: string; timestamp: string }>("/ready", {
      method: "GET",
    });
  },
};

