"""Conversational Response Service for EIP.

Handles natural conversational responses without document retrieval.
Used for greetings, capability questions, clarifications, and social chatter.
"""
import re
from typing import List, Optional
from backend.app.core.logging import logger
from backend.app.llm.base import LLMMessage
from backend.app.llm.router import llm_router


CONVERSATIONAL_SYSTEM_PROMPT = """You are a helpful and knowledgeable AI assistant for the Enterprise Intelligence Platform.
You are friendly, professional, and knowledgeable about engineering topics.

Your role is to:
1. Greet users warmly and professionally
2. Explain the platform's capabilities when asked
3. Help users understand how to use the platform effectively
4. Clarify previous responses when users are confused
4. Engage in natural, friendly conversation
5. For document-related questions, guide users to ask specific technical questions

Guidelines:
- Be conversational, friendly, and professional
- Keep responses concise but helpful
- Don't make up technical facts about the user's documents
- If asked about specific documents/incidents, guide them to ask specific questions
- Never make up technical details about their documents
- Be honest about what you can and cannot do

Example responses:
- "Hi! I'm here to help you explore your engineering documents..."
- "I can help you search your documents, investigate incidents, or explain technical concepts..."
- "I don't have access to that specific document, but if you upload it..."
"""

# Conversational response patterns for quick responses without LLM
GREETING_RESPONSES = [
    "Hello! I'm here to help you explore your engineering documents, investigate incidents, and analyze technical information. How can I assist you today?",
    "Hello! I'm your engineering intelligence assistant. I can help you search documents, investigate incidents, analyze technical issues, and answer questions grounded in your documentation. How can I help?",
    "Hello! I'm your Engineering Intelligence Assistant. I can search your technical documents, investigate incidents, analyze root causes, and answer questions with citations from your knowledge base. What can I help you with today?",
]

CAPABILITY_RESPONSES = [
    "I can help you:\n\n"
    "• **Search & Analyze Documents** - Search across all your indexed technical documents, incident reports, runbooks, and specifications\n"
    "• **Investigate Incidents** - Analyze root causes, timelines, and resolution steps for incidents\n"
    "• **Compare Documents** - Compare incidents, runbooks, or technical specifications side-by-side\n"
    "• **Answer Technical Questions** - Get grounded answers with citations from your documentation\n"
    "• **Analyze Metrics & Logs** - Extract and analyze metrics, logs, and performance data from your docs\n"
    "• **Generate Reports** - Create structured incident reports, postmortems, and summaries\n\n"
    "Just ask me a question about your documents, or try asking \"What happened in Incident 104?\" or \"Why did the API gateway return 504 errors?\"",
    
    "I'm your Engineering Intelligence Assistant. Here's what I can do:\n\n"
    "**Document Intelligence:**\n"
    "• Search across all indexed documents (incidents, runbooks, specs, postmortems)\n"
    "• Hybrid search combining semantic similarity and keyword matching\n"
    "• Source-grounded answers with inline citations [c_0], [c_1]...\n\n"
    "**Incident Investigation:**\n"
    "• Root cause analysis with evidence from your docs\n"
    "• Timeline reconstruction from logs and reports\n"
    "• Comparison of similar incidents\n\n"
    "**Technical Analysis:**\n"
    "• Architecture & infrastructure questions\n"
    "• Performance metrics, latency, error rates\n"
    "• Configuration, deployment, and infrastructure details\n\n"
    "**Anti-Hallucination Guarantees:**\n"
    "• Evidence sufficiency gate prevents hallucination\n"
    "• Automatic abstention when evidence is insufficient\n"
    "• Citation verification against source documents\n\n"
    "Just ask me anything about your engineering documentation!"
]

CLARIFICATION_RESPONSES = [
    "No problem! Could you tell me which part was unclear? I'm happy to break it down differently or provide more details.",
    "No problem! What specific part would you like me to clarify? I can rephrase, give an example, or break it down step by step.",
    "Of course! What part was confusing? I can rephrase, simplify, or dive deeper into any specific aspect.",
]

CLOSE_RESPONSES = [
    "You're welcome! Feel free to ask if you have more questions about your documents.",
    "You're welcome! Happy to help anytime you need to investigate your documents.",
    "You're welcome! Feel free to reach out anytime you need help with your engineering docs.",
]

SOCIAL_RESPONSES = [
    "I'm doing great, thank you for asking! How can I help you with your engineering documents today?",
    "I'm doing great, thanks for asking! Ready to help you investigate your engineering documents. What's on your mind?",
    "I'm doing well, thank you! How can I help you with your engineering documentation today?",
]


# Pattern-based quick responses (no LLM needed for common cases)
QUICK_RESPONSE_PATTERNS = [
    # Greetings
    (r"^\s*(hi|hello|hey|hiya|howdy|greetings)\b", "greeting"),
    (r"^\s*(good\s+(morning|afternoon|evening))\b", "greeting"),
    (r"^\s*(hey\s+there)\b", "greeting"),
    
    # Social
    (r"^\s*(how\s+are\s+you)\b", "social"),
    (r"^\s*(how's\s+it\s+going)\b", "social"),
    (r"^\s*(what's\s+up)\b", "social"),
    (r"^\s*(good\s+(morning|afternoon|evening))\b", "greeting"),
    
    # Capabilities
    (r"\b(how\s+can\s+you\s+help)\b", "capability"),
    (r"\b(what\s+can\s+you\s+do)\b", "capability"),
    (r"\b(what\s+are\s+your\s+(capabilities|features))\b", "capability"),
    (r"\b(what\s+is\s+this\s+(platform|system|tool))\b", "capability"),
    (r"\b(how\s+does\s+this\s+(work|platform))\b", "capability"),
    (r"\b(what\s+is\s+your\s+purpose)\b", "capability"),
    (r"\b(what\s+is\s+your\s+role)\b", "capability"),
    
    # Clarification
    (r"\b(i\s+don'?t\s+understand)\b", "clarification"),
    (r"\b(i\s+don't\s+get\s+it)\b", "clarification"),
    (r"\b(i'm\s+confused)\b", "clarification"),
    (r"\b(explain\s+(that|it)\s+(again|more|simply))\b", "clarification"),
    (r"\b(can\s+you\s+explain\s+(that|it)\s+(again|more|simply))\b", "clarification"),
    (r"\b(what\s+do\s+you\s+mean)\b", "clarification"),
    (r"\b(what\s+did\s+you\s+mean)\b", "clarification"),
    (r"\b(clarify)\b", "clarification"),
    (r"\b(elaborate)\b", "clarification"),
    
    # Close
    (r"^\s*(thank\s+you|thanks|thx)\b", "close"),
    (r"^\s*(goodbye|bye|bye-bye|see\s+you|see\s+ya)\b", "close"),
    (r"^\s*(okay|ok|okay)\.?\s*$", "close"),
    
    # Social
    (r"^\s*(how\s+are\s+you)\b", "social"),
    (r"^\s*(how's\s+it\s+going)\b", "social"),
    (r"^\s*(what's\s+up)\b", "social"),
]

# Response templates for each category
RESPONSE_TEMPLATES = {
    "greeting": GREETING_RESPONSES,
    "capability": CAPABILITY_RESPONSES,
    "clarification": CLARIFICATION_RESPONSES,
    "close": CLOSE_RESPONSES,
    "social": SOCIAL_RESPONSES,
}


def get_conversational_response(query: str, workspace_id: str = None, intent_type: str = None) -> Optional[str]:
    """
    Get a quick conversational response without LLM call for common patterns.
    Returns None if no pattern matches (should use LLM).
    """
    query_lower = query.lower().strip()
    
    for pattern, category in QUICK_RESPONSE_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            import random
            return random.choice(RESPONSE_TEMPLATES[category])
    
    return None


def get_llm_conversational_response(query: str, conversation_history: list = None) -> str:
    """
    Generate a conversational response using the LLM.
    Used when quick patterns don't match.
    """
    import random
    
    # Build conversation context
    history = ""
    if conversation_history:
        for msg in conversation_history[-6:]:  # Last 6 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]
            history += f"{role}: {content}\n"
    
    prompt = f"""You are a helpful Engineering Intelligence Platform assistant. Respond naturally and conversationally.

Conversation history:
{history}

User: {query}

Respond naturally and helpfully. Be concise but friendly. If the user is greeting you, greet them back and offer help. If they're asking about capabilities, explain what you can do. If they're confused, ask what to clarify."""
    
    try:
        messages = [
            LLMMessage(role="system", content=CONVERSATIONAL_SYSTEM_PROMPT),
            LLMMessage(role="user", content=prompt),
        ]
        response = llm_router.generate(messages=messages, temperature=0.7, max_tokens=500)
        return response.content
    except Exception as e:
        logger.error(f"Conversational LLM call failed: {e}")
        # Fallback to template
        return random.choice(GREETING_RESPONSES + CAPABILITY_RESPONSES)


def classify_intent(query: str) -> str:
    """
    Classify user intent for routing.
    Returns one of: 'conversational', 'document_question', 'mixed', 'unrelated'
    """
    query_lower = query.lower().strip()
    
    # Quick conversational patterns
    conversational_patterns = [
        r"^\s*(hi|hello|hey|hiya|howdy|greetings?)\b",
        r"^\s*(good\s+(morning|afternoon|evening))\b",
        r"^\s*(hey\s+there)\b",
        r"^\s*(how\s+are\s+you)\b",
        (r"^\s*(how's\s+it\s+going)\b", "social"),
        (r"^\s*(what's\s+up)\b", "social"),
        (r"^\s*(good\s+(morning|afternoon|evening))\b", "greeting"),
        (r"\b(how\s+can\s+you\s+help)\b", "capability"),
        (r"\b(what\s+can\s+you\s+do)\b", "capability"),
        (r"\b(what\s+are\s+your\s+(capabilities|features))\b", "capability"),
        (r"\b(what\s+is\s+this\s+(platform|system|tool))\b", "capability"),
        (r"\b(how\s+does\s+this\s+(work|platform))\b", "capability"),
        (r"\b(what\s+is\s+your\s+purpose)\b", "capability"),
        (r"\b(what\s+is\s+your\s+role)\b", "capability"),
        (r"\b(i\s+don'?t\s+understand)\b", "clarification"),
        (r"\b(i\s+don't\s+get\s+it)\b", "clarification"),
        (r"\b(i'm\s+confused)\b", "clarification"),
        (r"\b(explain\s+(that|it)\s+(again|more|simply))\b", "clarification"),
        (r"\b(can\s+you\s+explain\s+(that|it)\s+(again|more|simply))\b", "clarification"),
        (r"\b(what\s+do\s+you\s+mean)\b", "clarification"),
        (r"\b(what\s+did\s+you\s+mean)\b", "clarification"),
        (r"\b(clarify)\b", "clarification"),
        (r"\b(elaborate)\b", "clarification"),
        (r"^\s*(thank\s+you|thanks|thx)\b", "close"),
        (r"^\s*(goodbye|bye|bye-bye|see\s+you|see\s+ya)\b", "close"),
        (r"^\s*(okay|ok|okay)\.?\s*$", "close"),
        (r"^\s*(how\s+are\s+you)\b", "social"),
        (r"^\s*(how's\s+it\s+going)\b", "social"),
        (r"^\s*(what's\s+up)\b", "social"),
    ]
    
    for pattern, category in conversational_patterns:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return category
    
    # Check for document-related keywords
    doc_keywords = [
        "incident", "postmortem", "runbook", "architecture", "specification",
        "deployment", "infrastructure", "database", "database pool", "query",
        "latency", "timeout", "error", "error rate", "504", "500", "502", "503",
        "connection", "pool", "connection pool", "memory", "cpu", "disk",
        "latency", "throughput", "qps", "rps", "index", "indexes", "indexing",
        "token", "jwt", "auth", "authentication", "authorization",
        "runbook", "playbook", "api", "gateway", "service", "microservice",
        "database", "database pool", "redis", "kafka", "elasticsearch",
        "kubernetes", "k8s", "pod", "container", "aws", "gcp", "azure", "cloud",
        "ci", "cd", "pipeline", "deploy", "incident", "postmortem", "runbook",
        "architecture", "specification", "deployment", "infrastructure",
        "configuration", "config", "token", "jwt", "auth", "authentication",
        "authorization", "runbook", "playbook", "api", "gateway", "service",
        "microservice", "database", "database pool", "redis", "kafka",
        "elasticsearch", "kubernetes", "k8s", "pod", "container"
    ]
    
    query_lower = query.lower()
    for keyword in doc_keywords:
        if keyword in query_lower:
            return "document_question"
    
    # Default: could be conversational or edge case
    return "conversational"


# Global response cache for quick responses
_response_cache = {}

