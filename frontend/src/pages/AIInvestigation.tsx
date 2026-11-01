import React, { useState, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { chatService } from "@/services/chatService";
import { conversationService } from "@/services/conversationService";
import { ConversationItem, MessageItem, Citation, SearchResultItem } from "@/types";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import {
  Sparkles,
  Send,
  Plus,
  MessageSquare,
  Trash2,
  ShieldCheck,
  AlertTriangle,
  FileText,
  Search,
  ExternalLink,
  ChevronRight,
  Clock,
  Layers,
  Copy,
  Check,
  RotateCw,
  Cpu,
} from "lucide-react";

export const AIInvestigation: React.FC = () => {
  const { currentWorkspace } = useAuth();
  const [searchParams] = useSearchParams();

  // Conversation session state
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [activeCitations, setActiveCitations] = useState<Citation[]>([]);
  const [highlightedCitation, setHighlightedCitation] = useState<string | null>(null);

  // Input & Query state
  const [inputQuery, setInputQuery] = useState(searchParams.get("prompt") || "");
  const [isGenerating, setIsGenerating] = useState(false);
  const [topK, setTopK] = useState<number>(5);

  // Right Panel Tabs: "evidence" | "search"
  const [rightPanelTab, setRightPanelTab] = useState<"evidence" | "search">("evidence");
  const [explorerQuery, setExplorerQuery] = useState("");
  const [explorerResults, setExplorerResults] = useState<SearchResultItem[]>([]);
  const [isSearchingExplorer, setIsSearchingExplorer] = useState(false);
  const [explorerMode, setExplorerMode] = useState<"hybrid" | "dense" | "sparse">("hybrid");

  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadConversations = async () => {
    if (!currentWorkspace) return;
    try {
      const convList = await conversationService.listConversations(currentWorkspace.id);
      setConversations(convList);
    } catch (err) {
      console.error("Failed to load conversations:", err);
    }
  };

  useEffect(() => {
    loadConversations();
  }, [currentWorkspace]);

  // Load active conversation messages
  useEffect(() => {
    if (!activeConversationId || !currentWorkspace) return;

    conversationService
      .getConversation(currentWorkspace.id, activeConversationId)
      .then((conv) => {
        setMessages(conv.messages || []);
        // Extract citations from the last assistant message
        const lastAssistant = [...(conv.messages || [])].reverse().find((m) => m.role === "assistant");
        if (lastAssistant && lastAssistant.citations) {
          setActiveCitations(lastAssistant.citations);
        }
      })
      .catch((err) => console.error("Failed to load conversation details:", err));
  }, [activeConversationId, currentWorkspace]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isGenerating]);

  const handleSendMessage = async (queryToSend?: string) => {
    const text = (queryToSend || inputQuery).trim();
    if (!text || isGenerating || !currentWorkspace) return;

    const userTempMessage: MessageItem = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userTempMessage]);
    setInputQuery("");
    setIsGenerating(true);
    setHighlightedCitation(null);

    try {
      const response = await chatService.chat(currentWorkspace.id, {
        query: text,
        conversation_id: activeConversationId || undefined,
        top_k: topK,
      });

      const assistantMessage: MessageItem = {
        id: response.message_id,
        role: "assistant",
        content: response.answer,
        citations: response.citations,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setActiveCitations(response.citations || []);
      setActiveConversationId(response.conversation_id);
      await loadConversations();
    } catch (err: any) {
      const errorMessage: MessageItem = {
        id: `err-${Date.now()}`,
        role: "assistant",
        content: `**Error generating response:** ${err?.message || "Failed to communicate with RAG service"}`,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleStartNewConversation = () => {
    setActiveConversationId(null);
    setMessages([]);
    setActiveCitations([]);
    setInputQuery("");
    setHighlightedCitation(null);
  };

  const handleDeleteConversation = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!currentWorkspace) return;
    try {
      await conversationService.deleteConversation(currentWorkspace.id, convId);
      if (activeConversationId === convId) {
        handleStartNewConversation();
      }
      await loadConversations();
    } catch (err) {
      console.error("Failed to delete conversation:", err);
    }
  };

  const handleExplorerSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!explorerQuery.trim() || !currentWorkspace) return;

    setIsSearchingExplorer(true);
    try {
      const res = await chatService.search(currentWorkspace.id, {
        query: explorerQuery.trim(),
        top_k: 5,
        mode: explorerMode,
      });
      setExplorerResults(res.results || []);
    } catch (err) {
      console.error("Failed to execute search:", err);
    } finally {
      setIsSearchingExplorer(false);
    }
  };

  const handleCopy = (text: string, msgId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedMessageId(msgId);
    setTimeout(() => setCopiedMessageId(null), 2000);
  };

  const handleCitationClick = (marker: string) => {
    setRightPanelTab("evidence");
    setHighlightedCitation(marker);
    const elem = document.getElementById(`citation-${marker.replace(/[^a-zA-Z0-9]/g, "")}`);
    if (elem) {
      elem.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  return (
    <div className="h-[calc(100vh-6.5rem)] flex flex-col md:flex-row bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
      {/* ========================================================= */}
      {/* AREA 1: LEFT CONVERSATION SESSION PANEL (260px)           */}
      {/* ========================================================= */}
      <div className="w-full md:w-64 border-r border-slate-200/80 bg-slate-50 flex flex-col shrink-0">
        <div className="p-3 border-b border-slate-200/80 flex items-center justify-between">
          <Button
            size="sm"
            className="w-full justify-center"
            leftIcon={<Plus className="w-4 h-4" />}
            onClick={handleStartNewConversation}
          >
            New Investigation
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          <div className="px-2 py-1 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
            Recent Sessions
          </div>
          {conversations.length === 0 ? (
            <p className="text-[11px] text-slate-400 p-3 text-center">No past investigations</p>
          ) : (
            conversations.map((c) => (
              <div
                key={c.id}
                onClick={() => setActiveConversationId(c.id)}
                className={`w-full flex items-center justify-between p-2 rounded-lg text-xs cursor-pointer transition-colors group ${
                  activeConversationId === c.id
                    ? "bg-blue-100/70 text-blue-900 font-semibold border border-blue-200"
                    : "text-slate-700 hover:bg-slate-200/60"
                }`}
              >
                <div className="flex items-center gap-2 truncate flex-1 min-w-0">
                  <MessageSquare className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-600 shrink-0" />
                  <span className="truncate">{c.title || "Investigation"}</span>
                </div>
                <button
                  onClick={(e) => handleDeleteConversation(c.id, e)}
                  title="Delete Session"
                  className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-rose-600 transition-opacity ml-1"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* ========================================================= */}
      {/* AREA 2: CENTER AI INVESTIGATION CHAT                      */}
      {/* ========================================================= */}
      <div className="flex-1 flex flex-col bg-white min-w-0">
        {/* Chat Header */}
        <div className="h-12 border-b border-slate-200/80 px-4 flex items-center justify-between bg-white shrink-0">
          <div className="flex items-center gap-2 truncate">
            <Sparkles className="w-4 h-4 text-blue-600 shrink-0" />
            <span className="text-xs font-semibold text-slate-900 truncate">
              {activeConversationId
                ? conversations.find((c) => c.id === activeConversationId)?.title || "Active Investigation"
                : "New AI Investigation Session"}
            </span>
          </div>

          <div className="flex items-center gap-2 text-[11px] text-slate-500">
            <span>Retrieval budget:</span>
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="bg-slate-50 border border-slate-200 rounded px-2 py-0.5 text-xs text-slate-700 font-mono"
            >
              <option value={3}>Top 3</option>
              <option value={5}>Top 5</option>
              <option value={8}>Top 8</option>
            </select>
          </div>
        </div>

        {/* Messages Feed */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
          {messages.length === 0 ? (
            /* Starter Prompts and Empty State */
            <div className="h-full flex flex-col items-center justify-center max-w-xl mx-auto text-center px-4">
              <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mb-4 border border-blue-100">
                <Sparkles className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900">
                Ask Questions Grounded in Engineering Documents
              </h3>
              <p className="text-xs text-slate-500 mt-1.5 max-w-md">
                Every factual claim is cross-referenced with your indexed technical documentation, providing verified short citations [c_X].
              </p>

              {/* Starter Buttons */}
              <div className="w-full mt-6 space-y-2 text-left">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                  Suggested Investigations
                </p>
                {[
                  "What caused the database connection pool outage in Incident 104?",
                  "Why is API gateway latency increasing and how is 504 handled?",
                  "How does enterprise authentication work and what is token TTL?",
                  "Explain quantum teleportation entanglement protocols.",
                ].map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(q)}
                    className="w-full p-3 rounded-xl border border-slate-200/80 bg-slate-50/70 hover:bg-blue-50 hover:border-blue-200 text-xs text-slate-700 font-medium transition-colors flex items-center justify-between group"
                  >
                    <span>{q}</span>
                    <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600 shrink-0 ml-2" />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => {
              const isAssistant = msg.role === "assistant";
              const isAbstain = msg.content.includes("ABSTAIN: insufficient_evidence");

              return (
                <div
                  key={msg.id}
                  className={`flex gap-3 max-w-3xl ${isAssistant ? "" : "ml-auto justify-end"}`}
                >
                  {isAssistant && (
                    <div className="w-8 h-8 rounded-xl bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-xs mt-0.5">
                      <Sparkles className="w-4 h-4" />
                    </div>
                  )}

                  <div className={`space-y-2 min-w-0 ${isAssistant ? "flex-1" : "max-w-xl"}`}>
                    <div
                      className={`p-4 rounded-2xl text-xs leading-relaxed ${
                        isAssistant
                          ? "bg-slate-50/90 border border-slate-200/90 text-slate-800"
                          : "bg-blue-600 text-white font-medium shadow-xs"
                      }`}
                    >
                      {/* Abstention Banner */}
                      {isAssistant && isAbstain && (
                        <div className="mb-3 p-2.5 rounded-lg bg-amber-50 border border-amber-200 flex items-start gap-2 text-amber-800 text-xs">
                          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                          <div>
                            <span className="font-semibold block">Model Abstention Triggered</span>
                            <span className="text-[11px] text-amber-700">
                              The indexed documents do not contain verified technical evidence regarding this query.
                            </span>
                          </div>
                        </div>
                      )}

                      {/* Content */}
                      {isAssistant ? (
                        <MarkdownRenderer
                          content={msg.content}
                          onCitationClick={handleCitationClick}
                        />
                      ) : (
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                      )}
                    </div>

                    {/* Assistant Footer Telemetry & Actions */}
                    {isAssistant && (
                      <div className="flex items-center justify-between px-1 text-[11px] text-slate-400">
                        <div className="flex items-center gap-3">
                          {msg.citations && msg.citations.length > 0 && (
                            <span className="flex items-center gap-1 text-emerald-600 font-semibold">
                              <ShieldCheck className="w-3.5 h-3.5" />
                              <span>{msg.citations.length} Verified Sources</span>
                            </span>
                          )}
                        </div>

                        <button
                          onClick={() => handleCopy(msg.content, msg.id)}
                          className="flex items-center gap-1 hover:text-slate-600 transition-colors"
                        >
                          {copiedMessageId === msg.id ? (
                            <>
                              <Check className="w-3 h-3 text-emerald-500" />
                              <span className="text-emerald-500">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3 h-3" />
                              <span>Copy</span>
                            </>
                          )}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {isGenerating && (
            <div className="flex gap-3 max-w-3xl">
              <div className="w-8 h-8 rounded-xl bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-xs animate-pulse">
                <Sparkles className="w-4 h-4" />
              </div>
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 text-xs text-slate-500 flex items-center gap-2">
                <RotateCw className="w-4 h-4 text-blue-600 animate-spin" />
                <span>Retrieving evidence chunks & synthesizing source-grounded response...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-slate-200/80 bg-white shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              placeholder="Ask a technical question about your engineering documentation..."
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              disabled={isGenerating}
              className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all disabled:opacity-50"
            />
            <Button
              type="submit"
              size="md"
              disabled={!inputQuery.trim() || isGenerating}
              isLoading={isGenerating}
              leftIcon={<Send className="w-3.5 h-3.5" />}
            >
              Send
            </Button>
          </form>
        </div>
      </div>

      {/* ========================================================= */}
      {/* AREA 3: RIGHT EVIDENCE & CITATIONS PANEL (320px)          */}
      {/* ========================================================= */}
      <div className="w-full md:w-80 border-l border-slate-200/80 bg-slate-50 flex flex-col shrink-0">
        {/* Right Panel Tabs */}
        <div className="h-12 border-b border-slate-200/80 px-3 flex items-center gap-2 shrink-0 bg-slate-100/60">
          <button
            onClick={() => setRightPanelTab("evidence")}
            className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-colors flex items-center justify-center gap-1.5 ${
              rightPanelTab === "evidence"
                ? "bg-white text-slate-900 shadow-xs border border-slate-200"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>Citations ({activeCitations.length})</span>
          </button>
          <button
            onClick={() => setRightPanelTab("search")}
            className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-colors flex items-center justify-center gap-1.5 ${
              rightPanelTab === "search"
                ? "bg-white text-slate-900 shadow-xs border border-slate-200"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            <Search className="w-3.5 h-3.5 text-blue-600" />
            <span>Search Tool</span>
          </button>
        </div>

        {/* Tab 1: Sources & Citations */}
        {rightPanelTab === "evidence" && (
          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {activeCitations.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-400">
                <FileText className="w-8 h-8 text-slate-300 mb-2" />
                <p className="text-xs font-semibold text-slate-600">No active sources</p>
                <p className="text-[11px] text-slate-400 mt-1">
                  Ask a question in chat to view verified citation markers and document excerpts.
                </p>
              </div>
            ) : (
              activeCitations.map((cit) => {
                const isTarget = highlightedCitation === cit.marker;
                const cleanId = cit.marker.replace(/[^a-zA-Z0-9]/g, "");

                return (
                  <div
                    key={cit.chunk_id || cit.marker}
                    id={`citation-${cleanId}`}
                    className={`p-3.5 rounded-xl border bg-white transition-all text-xs space-y-2 ${
                      isTarget
                        ? "border-blue-500 ring-2 ring-blue-500/20 shadow-md"
                        : "border-slate-200/90 shadow-2xs hover:border-slate-300"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                        {cit.marker}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        score: {cit.score.toFixed(4)}
                      </span>
                    </div>

                    <p className="font-semibold text-slate-900 truncate text-[11px]">
                      {cit.document_title}
                    </p>

                    <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100 text-[11px] text-slate-700 leading-relaxed font-sans">
                      "{cit.snippet}..."
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* Tab 2: Knowledge Base Search Explorer */}
        {rightPanelTab === "search" && (
          <div className="flex-1 overflow-y-auto p-3 flex flex-col space-y-3">
            <form onSubmit={handleExplorerSearch} className="space-y-2 shrink-0">
              <input
                type="text"
                placeholder="Search raw chunks..."
                value={explorerQuery}
                onChange={(e) => setExplorerQuery(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <div className="flex items-center justify-between">
                <select
                  value={explorerMode}
                  onChange={(e) => setExplorerMode(e.target.value as any)}
                  className="bg-white border border-slate-200 rounded px-2 py-1 text-[11px] text-slate-700"
                >
                  <option value="hybrid">Hybrid (Dense+Sparse)</option>
                  <option value="dense">Dense (Vector)</option>
                  <option value="sparse">Sparse (BM25)</option>
                </select>
                <Button size="sm" type="submit" isLoading={isSearchingExplorer}>
                  Search
                </Button>
              </div>
            </form>

            <div className="flex-1 overflow-y-auto space-y-2 pr-1">
              {explorerResults.length === 0 ? (
                <p className="text-[11px] text-slate-400 text-center py-6">
                  {isSearchingExplorer ? "Searching..." : "Enter query to inspect chunks directly."}
                </p>
              ) : (
                explorerResults.map((r) => (
                  <div
                    key={r.chunk_id}
                    className="p-3 rounded-lg border border-slate-200 bg-white text-xs space-y-1.5"
                  >
                    <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                      <span className="truncate max-w-[140px] text-slate-800 font-semibold font-sans">
                        {r.document_title}
                      </span>
                      <span>score {r.score.toFixed(4)}</span>
                    </div>
                    <p className="text-[11px] text-slate-600 line-clamp-3">{r.content}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

