import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { conversationService } from "@/services/conversationService";
import { ConversationItem } from "@/types";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import {
  MessageSquare,
  Search,
  Trash2,
  ArrowRight,
  Clock,
  Sparkles,
  Calendar,
} from "lucide-react";

export const Conversations: React.FC = () => {
  const { currentWorkspace } = useAuth();
  const navigate = useNavigate();

  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  const [convToDelete, setConvToDelete] = useState<ConversationItem | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const loadConversations = async () => {
    if (!currentWorkspace) return;
    setIsLoading(true);
    try {
      const data = await conversationService.listConversations(currentWorkspace.id);
      setConversations(data);
    } catch (err) {
      console.error("Failed to load conversations:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadConversations();
  }, [currentWorkspace]);

  const handleDelete = async () => {
    if (!convToDelete || !currentWorkspace) return;
    setIsDeleting(true);
    try {
      await conversationService.deleteConversation(currentWorkspace.id, convToDelete.id);
      setConvToDelete(null);
      await loadConversations();
    } catch (err) {
      console.error("Failed to delete conversation:", err);
    } finally {
      setIsDeleting(false);
    }
  };

  const filtered = conversations.filter((c) =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Conversations</h1>
          <p className="text-xs text-slate-500 mt-1">
            Archived and active technical investigation sessions and evidence traces.
          </p>
        </div>
        <Button
          leftIcon={<Sparkles className="w-4 h-4" />}
          onClick={() => navigate("/chat")}
        >
          New Investigation
        </Button>
      </div>

      {/* Search Bar */}
      <Card>
        <CardContent className="p-4">
          <Input
            placeholder="Search conversations by title or topic..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            leftIcon={<Search className="w-4 h-4" />}
          />
        </CardContent>
      </Card>

      {/* Conversations Grid */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-slate-400">Loading conversations...</div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <MessageSquare className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <p className="text-sm font-semibold text-slate-700">No conversations found</p>
            <p className="text-xs text-slate-400 mt-1">
              Start an AI investigation to build a conversational knowledge history.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-4"
              onClick={() => navigate("/chat")}
            >
              Start Chat
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((conv) => (
            <Card key={conv.id} hover className="flex flex-col justify-between">
              <CardContent className="p-5 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                    <MessageSquare className="w-4 h-4" />
                  </div>
                  <button
                    onClick={() => setConvToDelete(conv)}
                    title="Delete Conversation"
                    className="text-slate-400 hover:text-rose-600 p-1 rounded hover:bg-slate-100 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-slate-900 line-clamp-2">
                    {conv.title || "Untitled Session"}
                  </h3>
                  {conv.summary && (
                    <p className="text-xs text-slate-500 line-clamp-2 mt-1">{conv.summary}</p>
                  )}
                </div>

                <div className="flex items-center gap-3 text-[11px] text-slate-400 pt-2 border-t border-slate-100">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    <span>{new Date(conv.updated_at).toLocaleDateString()}</span>
                  </span>
                  <span>•</span>
                  <span>{conv.messages?.length || 0} messages</span>
                </div>
              </CardContent>

              <div className="p-3 bg-slate-50/70 border-t border-slate-100 rounded-b-xl flex justify-end">
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-blue-600 hover:text-blue-700 text-xs gap-1 font-semibold"
                  onClick={() => navigate(`/chat?conversationId=${conv.id}`)}
                >
                  <span>Continue Investigation</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!convToDelete}
        onClose={() => setConvToDelete(null)}
        title="Delete Conversation Session"
        description="Are you sure you want to permanently delete this conversation and its citation history?"
        size="sm"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-600">
            Deleting <strong className="text-slate-900">{convToDelete?.title}</strong> cannot be undone.
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setConvToDelete(null)}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="danger"
              onClick={handleDelete}
              isLoading={isDeleting}
            >
              Delete
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

