import { request } from "./api";
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

  async deleteDocument(workspaceId: string, documentId: string): Promise<void> {
    return request<void>(
      `/api/v1/workspaces/${workspaceId}/documents/${documentId}`,
      {
        method: "DELETE",
      }
    );
  },
};

