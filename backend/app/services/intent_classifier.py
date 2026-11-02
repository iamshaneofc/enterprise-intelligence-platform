"""Intent Classification Service for EIP.

Classifies user messages into conversational vs document-grounded intents.
Uses a lightweight heuristic + keyword-based approach for fast routing.
"""
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class IntentType(str, Enum):
    """Types of user intent."""
    GREETING = "greeting"  # hi, hello, hey, good morning
    CAPABILITY_QUESTION = "capability_question"  # how can you help, what can you do
    CLARIFICATION_FOLLOWUP = "clarification_followup"  # explain that again, I don't understand
    CONVERSATIONAL_CLOSE = "conversational_close"  # thank you, goodbye, bye
    SOCIAL_CHATTER = "social_chatter"  # how are you, good morning
    DOCUMENT_QUESTION = "document_question"  # technical questions about docs
    MIXED_CONVERSATIONAL_DOC = "mixed_conversational_doc"  # mixed conversational + doc question
    UNRELATED_QUESTION = "unrelated_question"  # outside knowledge base


class IntentClassification(BaseModel):
    """Result of intent classification."""
    intent_type: IntentType
    confidence: float
    is_conversational: bool
    should_use_rag: bool
    reasoning: str


class IntentClassifier:
    """
    Lightweight intent classifier for routing user messages.
    
    Uses keyword-based heuristics for fast classification without additional LLM calls.
    Designed to be fast and deterministic.
    """
    
    # Greeting patterns
    GREETING_PATTERNS = [
        r"^\s*(hi|hello|hey|hiya|howdy|greetings?)\b",
        r"^\s*(good\s+(morning|afternoon|evening))\b",
        r"^\s*(hey\s+there)\b",
    ]
    
    # Capability/Help question patterns
    CAPABILITY_PATTERNS = [
        r"\b(how\s+can\s+you\s+help)\b",
        r"\b(what\s+can\s+you\s+do)\b",
        r"\b(what\s+are\s+your\s+(capabilities|features))\b",
        r"\b(what\s+is\s+this\s+(platform|system|tool))\b",
        r"\b(how\s+does\s+this\s+(work|platform))\b",
        r"\b(what\s+is\s+your\s+purpose)\b",
    ]
    
    # Clarification/Follow-up patterns
    CLARIFICATION_PATTERNS = [
        r"\b(i\s+don'?t\s+understand)\b",
        r"\b(i\s+don't\s+get\s+it)\b",
        r"\b(i'm\s+confused)\b",
        r"\b(explain\s+(that|it)\s+(again|more|simply))\b",
        r"\b(can\s+you\s+explain\s+(that|it)\s+(again|more|simply))\b",
        r"\b(what\s+do\s+you\s+mean)\b",
        r"\b(what\s+did\s+you\s+mean)\b",
        r"\b(clarify)\b",
        r"\b(elaborate)\b",
    ]
    
    # Conversational close patterns
    CLOSE_PATTERNS = [
        r"^\s*(thank\s+you|thanks|thx)\b",
        r"^\s*(goodbye|bye|bye-bye|see\s+you|see\s+ya)\b",
        r"^\s*(okay|ok|okay)\.?\s*$",
    ]
    
    # Social chatter patterns
    SOCIAL_CHATTER_PATTERNS = [
        r"^\s*(how\s+are\s+you)\b",
        r"^\s*(how's\s+it\s+going)\b",
        r"^\s*(what's\s+up)\b",
        r"^\s*(how\s+do\s+you\s+do)\b",
        r"^\s*(nice\s+to\s+meet\s+you)\b",
        r"^\s*(good\s+(morning|afternoon|evening))\b",
    ]
    
    # Document/Technical question indicators
    DOCUMENT_QUESTION_PATTERNS = [
        r"\b(what\s+(caused|happened|was\s+the\s+cause))\b",
        r"\b(why\s+(did|is|was))\b",
        r"\b(how\s+(did|does|to))\b",
        r"\b(what\s+(is|was|are|were)\s+the)\b",
        r"\b(when\s+(did|was|were))\b",
        r"\b(where\s+(did|is|was))\b",
        r"\b(who\s+(did|is|was))\b",
        r"\b(which\s+(service|component|service|component))\b",
        r"\b(incident\s+\d+)\b",
        r"\b(root\s+cause)\b",
        r"\b(postmortem)\b",
        r"\b(runbook)\b",
        r"\b(architecture)\b",
        r"\b(specification|spec)\b",
        r"\b(configuration|config)\b",
        r"\b(deployment|deploy)\b",
        r"\b(infrastructure)\b",
        r"\b(database|db)\b",
        r"\b(query|queries)\b",
        r"\b(latency|timeout|error|error\s+rate|504|500|502|503)\b",
        r"\b(connection|pool|connection\s+pool)\b",
        r"\b(memory|cpu|disk|disk\s+usage|cpu\s+usage)\b",
        r"\b(latency|throughput|throughput|qps|rps)\b",
        r"\b(index|indexes|indexing)\b",
        r"\b(query|queries)\b",
        r"\b(token|jwt|auth|authentication|authorization)\b",
        r"\b(runbook|playbook)\b",
        r"\b(api|gateway|service|microservice)\b",
        r"\b(database|database\s+pool)\b",
        r"\b(redis|kafka|kafka|elasticsearch)\b",
        r"\b(kubernetes|k8s|pod|container)\b",
        r"\b(aws|gcp|azure|cloud)\b",
        r"\b(ci|cd|pipeline|deploy)\b",
    ]
    
    # Unrelated/Off-topic indicators
    UNRELATED_PATTERNS = [
        r"\b(recipe|cook|food|restaurant)\b",
        r"\b(movie|movie|film|netflix)\b",
        r"\b(sports|football|basketball|soccer)\b",
        r"\b(weather|weather\s+forecast)\b",
        r"\b(news|politics|election)\b",
        r"\b(celebrity|gossip)\b",
        r"\b(game|gaming|playstation|xbox)\b",
        r"\b(crypto|bitcoin|ethereum|blockchain)\b",
        r"\b(stock|stocks|investment)\b",
        r"\b(joke|funny|humor)\b",
        r"\b(poem|poetry|creative\s+writing)\b",
        r"\b(quantum\s+teleportation)\b",
        r"\b(entanglement)\b",
        r"\b(philosophy|meaning\s+of\s+life)\b",
    ]

    def __init__(self):
        # Compile all patterns
        self._compiled_greetings = [re.compile(p, re.IGNORECASE) for p in self.GREETING_PATTERNS]
        self._compiled_capability = [re.compile(p, re.IGNORECASE) for p in self.CAPABILITY_PATTERNS]
        self._compiled_clarification = [re.compile(p, re.IGNORECASE) for p in self.CLARIFICATION_PATTERNS]
        self._compiled_close = [re.compile(p, re.IGNORECASE) for p in self.CLOSE_PATTERNS]
        self._compiled_social = [re.compile(p, re.IGNORECASE) for p in self.SOCIAL_CHATTER_PATTERNS]
        self._compiled_doc = [re.compile(p, re.IGNORECASE) for p in self.DOCUMENT_QUESTION_PATTERNS]
        self._compiled_unrelated = [re.compile(p, re.IGNORECASE) for p in self.UNRELATED_PATTERNS]

    def classify(self, query: str, conversation_history: Optional[List[str]] = None) -> IntentClassification:
        """
        Classify the user's intent.
        
        Args:
            query: The user's message
            conversation_history: Optional list of previous messages for context
            
        Returns:
            IntentClassification with intent type and routing decision
        """
        if not query or not query.strip():
            return IntentClassification(
                intent_type=IntentType.GREETING,
                confidence=0.5,
                is_conversational=True,
                should_use_rag=False,
                reasoning="Empty query treated as greeting"
            )
        
        query_lower = query.lower().strip()
        
        # Check for greetings (highest priority for conversational)
        if self._matches_any(query_lower, self._compiled_greetings):
            return IntentClassification(
                intent_type=IntentType.GREETING,
                confidence=0.95,
                is_conversational=True,
                should_use_rag=False,
                reasoning="Detected greeting pattern"
            )
        
        # Check for social chatter
        if self._matches_any(query_lower, self._compiled_social):
            return IntentClassification(
                intent_type=IntentType.SOCIAL_CHATTER,
                confidence=0.9,
                is_conversational=True,
                should_use_rag=False,
                reasoning="Detected social chatter"
            )
        
        # Check for conversational close
        if self._matches_any(query_lower, self._compiled_close):
            return IntentClassification(
                intent_type=IntentType.CONVERSATIONAL_CLOSE,
                confidence=0.95,
                is_conversational=True,
                should_use_rag=False,
                reasoning="Detected conversational close"
            )
        
        # Check for capability/help questions
        if self._matches_any(query_lower, self._compiled_capability):
            return IntentClassification(
                intent_type=IntentType.CAPABILITY_QUESTION,
                confidence=0.9,
                is_conversational=True,
                should_use_rag=False,
                reasoning="Detected capability/help question"
            )
        
        # Check for clarification/follow-up
        if self._matches_any(query_lower, self._compiled_clarification):
            # If we have conversation history, it's likely a follow-up
            is_followup = bool(conversation_history and len(conversation_history) > 0)
            return IntentClassification(
                intent_type=IntentType.CLARIFICATION_FOLLOWUP,
                confidence=0.85,
                is_conversational=True,
                should_use_rag=is_followup,  # Use RAG if follow-up to doc question
                reasoning="Detected clarification/follow-up request"
            )
        
        # Check for unrelated/off-topic questions
        if self._matches_any(query_lower, self._compiled_unrelated):
            return IntentClassification(
                intent_type=IntentType.UNRELATED_QUESTION,
                confidence=0.9,
                is_conversational=True,
                should_use_rag=True,  # Let RAG pipeline handle it - evidence gate will abstain
                reasoning="Detected off-topic/unrelated question - routing to RAG for evidence gate"
            )
        
        # Check for document/technical questions
        if self._matches_any(query_lower, self._compiled_doc):
            # Check if it's mixed with conversational elements
            is_conversational = self._has_conversational_elements(query_lower)
            if is_conversational:
                return IntentClassification(
                    intent_type=IntentType.MIXED_CONVERSATIONAL_DOC,
                    confidence=0.75,
                    is_conversational=True,
                    should_use_rag=True,  # Still use RAG for factual parts
                    reasoning="Document question with conversational elements"
                )
            else:
                return IntentClassification(
                    intent_type=IntentType.DOCUMENT_QUESTION,
                    confidence=0.9,
                    is_conversational=False,
                    should_use_rag=True,
                    reasoning="Detected document/technical question"
                )
        
        # Default: treat as potential document question, but low confidence
        # Could be a new type of query or edge case
        return IntentClassification(
            intent_type=IntentType.DOCUMENT_QUESTION,
            confidence=0.4,
            is_conversational=False,
            should_use_rag=True,
            reasoning="No clear intent detected, defaulting to document search"
        )
    
    def _matches_any(self, text: str, patterns: List[re.Pattern]) -> bool:
        """Check if text matches any of the compiled patterns."""
        return any(p.search(text) for p in patterns)
    
    def _has_conversational_elements(self, query: str) -> bool:
        """Check if query has conversational elements mixed with document query."""
        conversational_indicators = [
            "can you", "could you", "would you", "please", "thanks", "thank you",
            "i want to", "i'd like to", "i want to", "i need to",
            "help me", "can you help", "please explain", "could you explain"
        ]
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in conversational_indicators)


# Global instance
intent_classifier = IntentClassifier()