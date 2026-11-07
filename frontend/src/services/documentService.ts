import { request, API_BASE_URL, getAuthToken } from "./api";
import { DocumentItem, ChunkItem } from "@/types";

export interface UploadDocumentResponse {
  message: string;
  document: DocumentItem;
}

export const documentService = {
  async uploadDocument(workspaceId: string, file: File): Promise<UploadDocumentResponse> {
    const formData = new FormData();
    formData.append("file", file);

    return request<UploadDocumentResponse>(
      `/api/v1/workspaces/${workspaceId}/documents/upload`,
      {
        method: "POST",
        body: formData,
      }
    );
  },

  async listDocuments(workspaceId: string): Promise<DocumentItem[]> {
    return request<DocumentItem[]>(
      `/api/v1/workspaces/${workspaceId}/documents`,
      {
        method: "GET",
      }
    );
  },

  async getDocument(workspaceId: string, documentId: string): Promise<DocumentItem> {
    return request<DocumentItem>(
      `/api/v1/workspaces/${workspaceId}/documents/${documentId}`,
      {
        method: "GET",
      }
    );
  },

  async getDocumentChunks(workspaceId: string, documentId: string): Promise<ChunkItem[]> {
    return request<ChunkItem[]>(
      `/api/v1/workspaces/${workspaceId}/documents/${documentId}/chunks`,
      {
        method: "GET",
      }
    );
  },

  async downloadDocument(workspaceId: string, documentId: string, filename: string): Promise<void> {
    const token = getAuthToken();
    const url = `${API_BASE_URL}/api/v1/workspaces/${workspaceId}/documents/${documentId}/download`;

    const res = await fetch(url, {
      method: "GET",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to download document" }));
      throw new Error(err.detail || `Download failed with status ${res.status}`);
    }

    const blob = await res.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  },

  async deleteDocument(workspaceId: string, documentId: string): Promise<void> {
    return request<void>(
      `/api/v1/workspaces/${workspaceId}/documents/${documentId}`,
      {
        method: "DELETE",
      }
    );
  },
};

