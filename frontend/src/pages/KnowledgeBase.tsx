import React, { useState, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { documentService } from "@/services/documentService";
import { DocumentItem, ChunkItem } from "@/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import {
  Upload,
  FileText,
  Search,
  Trash2,
  Eye,
  CheckCircle2,
  AlertCircle,
  FileUp,
  Layers,
  Calendar,
  HardDrive,
  Hash,
  X,
  FileSpreadsheet,
  FileCode,
  Sparkles,
  Download,
} from "lucide-react";

export const KnowledgeBase: React.FC = () => {
  const { currentWorkspace } = useAuth();
  const [searchParams] = useSearchParams();

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState(searchParams.get("search") || "");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");

  // Upload modal state
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(
    searchParams.get("action") === "upload"
  );
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccessMessage, setUploadSuccessMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Document details / chunk explorer modal state
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null);
  const [chunks, setChunks] = useState<ChunkItem[]>([]);
  const [isLoadingChunks, setIsLoadingChunks] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [docToDelete, setDocToDelete] = useState<DocumentItem | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [downloadingDocId, setDownloadingDocId] = useState<string | null>(null);

  const loadDocuments = async () => {
    if (!currentWorkspace) return;
    setIsLoading(true);
    try {
      const data = await documentService.listDocuments(currentWorkspace.id);
      setDocuments(data);

      // Check if doc was specified in URL params
      const targetDocId = searchParams.get("doc");
      if (targetDocId) {
        const found = data.find((d) => d.id === targetDocId);
        if (found) handleOpenDocDetails(found);
      }
    } catch (err) {
      console.error("Failed to load documents:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [currentWorkspace]);

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !currentWorkspace) return;

    setIsUploading(true);
    setUploadError(null);
    setUploadSuccessMessage(null);

    try {
      const res = await documentService.uploadDocument(currentWorkspace.id, selectedFile);
      setUploadSuccessMessage(res.message || "Document uploaded and indexed successfully!");
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await loadDocuments();
      setTimeout(() => {
        setIsUploadModalOpen(false);
        setUploadSuccessMessage(null);
      }, 1500);
    } catch (err: any) {
      setUploadError(err?.message || "Failed to upload document");
    } finally {
      setIsUploading(false);
    }
  };

  const handleOpenDocDetails = async (doc: DocumentItem) => {
    setSelectedDoc(doc);
    if (!currentWorkspace) return;
    setIsLoadingChunks(true);
    try {
      const chunkData = await documentService.getDocumentChunks(currentWorkspace.id, doc.id);
      setChunks(chunkData);
    } catch (err) {
      console.error("Failed to load chunks:", err);
    } finally {
      setIsLoadingChunks(false);
    }
  };

  const handleDeleteDocument = async () => {
    if (!docToDelete || !currentWorkspace) return;
    setIsDeleting(true);
    try {
      await documentService.deleteDocument(currentWorkspace.id, docToDelete.id);
      setIsDeleteModalOpen(false);
      setDocToDelete(null);
      if (selectedDoc?.id === docToDelete.id) {
        setSelectedDoc(null);
      }
      await loadDocuments();
    } catch (err: any) {
      console.error("Failed to delete document:", err);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDownloadDocument = async (doc: DocumentItem) => {
    if (!currentWorkspace) return;
    try {
      setDownloadingDocId(doc.id);
      await documentService.downloadDocument(currentWorkspace.id, doc.id, doc.filename);
    } catch (err: any) {
      console.error("Failed to download document:", err);
      alert(err.message || "Failed to download document");
    } finally {
      setDownloadingDocId(null);
    }
  };

  // Filtered documents
  const filteredDocuments = documents.filter((doc) => {
    const matchesSearch =
      doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.filename.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || doc.status === statusFilter;
    const matchesType = typeFilter === "all" || doc.file_type.toLowerCase() === typeFilter.toLowerCase();
    return matchesSearch && matchesStatus && matchesType;
  });

  const getFileIcon = (type: string) => {
    const clean = type.toLowerCase();
    if (clean === "pdf") return <FileText className="w-4 h-4 text-rose-500" />;
    if (clean === "csv") return <FileSpreadsheet className="w-4 h-4 text-emerald-500" />;
    if (clean === "json" || clean === "md") return <FileCode className="w-4 h-4 text-blue-500" />;
    return <FileText className="w-4 h-4 text-slate-500" />;
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Knowledge Base</h1>
          <p className="text-xs text-slate-500 mt-1">
            Manage engineering documents, runbooks, specifications, and inspect chunked vector embeddings.
          </p>
        </div>
        <Button
          leftIcon={<Upload className="w-4 h-4" />}
          onClick={() => {
            setUploadError(null);
            setUploadSuccessMessage(null);
            setIsUploadModalOpen(true);
          }}
        >
          Upload Document
        </Button>
      </div>

      {/* Filter and Search Bar */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
            <div className="w-full sm:w-80">
              <Input
                placeholder="Search documents by title or filename..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                leftIcon={<Search className="w-4 h-4" />}
              />
            </div>
            <div className="flex items-center gap-2 w-full sm:w-auto">
              {/* Status Filter */}
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Statuses</option>
                <option value="completed">Completed</option>
                <option value="processing">Processing</option>
                <option value="failed">Failed</option>
              </select>

              {/* Type Filter */}
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="bg-white border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Formats</option>
                <option value="pdf">PDF</option>
                <option value="md">Markdown (.md)</option>
                <option value="txt">Plain Text (.txt)</option>
                <option value="csv">CSV (.csv)</option>
                <option value="json">JSON (.json)</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Documents Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-12 text-center text-xs text-slate-400">Loading documents...</div>
          ) : filteredDocuments.length === 0 ? (
            <div className="p-12 text-center">
              <FileText className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-700">No documents found</p>
              <p className="text-xs text-slate-400 mt-1">
                {searchQuery || statusFilter !== "all" || typeFilter !== "all"
                  ? "Try adjusting your filters or search query."
                  : "Upload a technical runbook or postmortem to get started."}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200/80 text-slate-500 uppercase tracking-wider font-semibold text-[10px]">
                  <tr>
                    <th className="px-6 py-3.5">Document Title</th>
                    <th className="px-4 py-3.5">Format</th>
                    <th className="px-4 py-3.5">Size</th>
                    <th className="px-4 py-3.5">Chunks</th>
                    <th className="px-4 py-3.5">Status</th>
                    <th className="px-4 py-3.5">Uploaded</th>
                    <th className="px-6 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {filteredDocuments.map((doc) => (
                    <tr
                      key={doc.id}
                      className="hover:bg-slate-50/70 transition-colors cursor-pointer group"
                      onClick={() => handleOpenDocDetails(doc)}
                    >
                      <td className="px-6 py-4 font-semibold text-slate-900 flex items-center gap-2.5">
                        <span className="p-1.5 rounded bg-slate-100 shrink-0">
                          {getFileIcon(doc.file_type)}
                        </span>
                        <div className="min-w-0">
                          <span className="truncate block font-medium group-hover:text-blue-600 transition-colors">
                            {doc.title}
                          </span>
                          <span className="text-[10px] text-slate-400 font-mono block mt-0.5">
                            {doc.filename}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-4 uppercase font-mono text-[11px] text-slate-500">
                        {doc.file_type}
                      </td>
                      <td className="px-4 py-4 text-slate-500">
                        {(doc.file_size_bytes / 1024).toFixed(1)} KB
                      </td>
                      <td className="px-4 py-4 font-mono font-medium text-slate-900">
                        {doc.chunk_count}
                      </td>
                      <td className="px-4 py-4">
                        <Badge
                          variant={
                            doc.status === "completed"
                              ? "success"
                              : doc.status === "processing"
                              ? "primary"
                              : doc.status === "failed"
                              ? "danger"
                              : "warning"
                          }
                          size="sm"
                          dot
                        >
                          {doc.status}
                        </Badge>
                      </td>
                      <td className="px-4 py-4 text-slate-500">
                        {new Date(doc.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => handleDownloadDocument(doc)}
                            title="Download Original File"
                            disabled={downloadingDocId === doc.id}
                            className="p-1.5 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-md transition-colors disabled:opacity-50"
                          >
                            <Download className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleOpenDocDetails(doc)}
                            title="Inspect Chunks"
                            className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => {
                              setDocToDelete(doc);
                              setIsDeleteModalOpen(true);
                            }}
                            title="Delete Document"
                            className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-md transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Upload Document Modal */}
      <Modal
        isOpen={isUploadModalOpen}
        onClose={() => {
          if (!isUploading) setIsUploadModalOpen(false);
        }}
        title="Upload Technical Document"
        description="Supported formats: PDF, Markdown (.md), Plain Text (.txt), CSV (.csv), JSON (.json). Maximum 50 MB."
      >
        <form onSubmit={handleFileUpload} className="space-y-4">
          {uploadError && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 flex items-start gap-2.5 text-xs text-rose-700">
              <AlertCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
              <span>{uploadError}</span>
            </div>
          )}

          {uploadSuccessMessage && (
            <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 flex items-start gap-2.5 text-xs text-emerald-700">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
              <span>{uploadSuccessMessage}</span>
            </div>
          )}

          {/* Drag & Drop Zone */}
          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-slate-300 hover:border-blue-500 rounded-xl p-8 text-center cursor-pointer transition-colors bg-slate-50/50 hover:bg-blue-50/20"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.md,.txt,.csv,.json"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setSelectedFile(e.target.files[0]);
                }
              }}
            />
            <FileUp className="w-10 h-10 text-blue-500 mx-auto mb-3" />
            <p className="text-xs font-semibold text-slate-700">
              {selectedFile ? selectedFile.name : "Click or drag & drop file to upload"}
            </p>
            <p className="text-[11px] text-slate-400 mt-1">
              Automatic SHA-256 deduplication and 1536-dim vector embedding
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsUploadModalOpen(false)}
              disabled={isUploading}
            >
              Cancel
            </Button>
            <Button type="submit" isLoading={isUploading} disabled={!selectedFile}>
              Upload & Index
            </Button>
          </div>
        </form>
      </Modal>

      {/* Document Details & Chunk Explorer Modal */}
      {selectedDoc && (
        <Modal
          isOpen={!!selectedDoc}
          onClose={() => setSelectedDoc(null)}
          title={selectedDoc.title}
          description={`Document Details and Chunk Index (${selectedDoc.chunk_count} chunks)`}
          size="xl"
        >
          <div className="space-y-6">
            {/* Metadata Summary */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Format</span>
                <span className="font-semibold text-slate-700 uppercase">{selectedDoc.file_type}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">File Size</span>
                <span className="font-semibold text-slate-700">
                  {(selectedDoc.file_size_bytes / 1024).toFixed(1)} KB
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Status</span>
                <span className="font-semibold text-emerald-600">{selectedDoc.status}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">SHA-256</span>
                <span className="font-mono text-[10px] text-slate-600 truncate block">
                  {selectedDoc.file_hash.slice(0, 12)}...
                </span>
              </div>
            </div>

            {/* Chunks List */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                  <Layers className="w-3.5 h-3.5 text-blue-600" />
                  <span>Indexed Vector Chunks</span>
                </h4>
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={() => handleDownloadDocument(selectedDoc)}
                  disabled={downloadingDocId === selectedDoc.id}
                  className="flex items-center gap-1.5 text-xs text-slate-700 hover:text-emerald-600 hover:bg-emerald-50"
                >
                  <Download className="w-3.5 h-3.5 text-emerald-600" />
                  <span>{downloadingDocId === selectedDoc.id ? "Downloading..." : "Download Original File"}</span>
                </Button>
              </div>

              {isLoadingChunks ? (
                <div className="p-8 text-center text-xs text-slate-400">Loading chunks...</div>
              ) : chunks.length === 0 ? (
                <p className="text-xs text-slate-400">No chunks indexed for this document.</p>
              ) : (
                <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
                  {chunks.map((ch) => (
                    <div
                      key={ch.id}
                      className="p-3.5 rounded-lg border border-slate-200 bg-white text-xs space-y-2 hover:border-slate-300 transition-colors"
                    >
                      <div className="flex items-center justify-between text-[11px] text-slate-500 border-b border-slate-100 pb-2">
                        <span className="font-mono font-semibold text-blue-600">
                          Chunk #{ch.chunk_index}
                        </span>
                        <div className="flex items-center gap-3">
                          {ch.chunk_metadata?.page_number && (
                            <span>Page {ch.chunk_metadata.page_number}</span>
                          )}
                          {ch.chunk_metadata?.token_count && (
                            <span>~{ch.chunk_metadata.token_count} tokens</span>
                          )}
                        </div>
                      </div>

                      {ch.chunk_metadata?.section_header && (
                        <p className="text-[11px] font-semibold text-slate-800">
                          Section: {ch.chunk_metadata.section_header}
                        </p>
                      )}

                      <p className="text-slate-700 leading-relaxed font-sans bg-slate-50/50 p-2 rounded border border-slate-100">
                        {ch.content}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </Modal>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        title="Delete Technical Document"
        description="Are you sure you want to permanently delete this document and all its indexed vector chunks?"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-600">
            Deleting <strong className="text-slate-900">{docToDelete?.title}</strong> will immediately remove all indexed embeddings from vector search.
          </p>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsDeleteModalOpen(false)}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="danger"
              onClick={handleDeleteDocument}
              isLoading={isDeleting}
            >
              Delete Document
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
