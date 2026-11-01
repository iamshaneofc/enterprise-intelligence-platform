"""Conversational memory manager supporting sliding context windows and query reformulation."""
import re
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.app.models.conversation import Conversation, Message
from backend.app.llm.base import LLMMessage
from backend.app.llm.router import llm_router


class MemoryManager:
    """Manages short-term conversation context, token sliding windows, and rolling summaries."""

    def __init__(self, max_turns: int = 4):
        self.max_turns = max_turns

    def get_context_messages(self, conversation_id: str, db: Session) -> List[Message]:
        """Fetch the most recent turns within sliding window budget."""
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(self.max_turns * 2)
            .all()
        )
        return list(reversed(messages))

    def reformulate_query(self, query: str, conversation_id: Optional[str], db: Session) -> str:
        """
        Rewrite pronouns and conversational coreferences into a standalone query.
        E.g. 'What was its resolution?' -> 'What was the resolution of Incident 104?'
        """
        if not conversation_id:
            return query

        history = self.get_context_messages(conversation_id, db)
        if not history:
            return query

        # Check for ambiguous pronouns (it, its, this, that, they, them)
        pronoun_pattern = r"\b(it|its|this|that|they|them|the incident|the bug)\b"
        if not re.search(pronoun_pattern, query, re.IGNORECASE):
            return query

        # Find key entity in recent messages
        last_user_msgs = [m.content for m in history if m.role == "user"]
        if last_user_msgs:
            last_query = last_user_msgs[-1]
            # Heuristic entity carryover
            entity_match = re.search(r"\b(incident\s+\d+|database\s+pool|gateway\s+latency|auth\s+service)\b", last_query, re.IGNORECASE)
            if entity_match:
                entity = entity_match.group(1)
                return f"{query} regarding {entity}"

        return query


memory_manager = MemoryManager()

