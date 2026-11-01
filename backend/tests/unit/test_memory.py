"""Unit tests for conversational memory and query reformulation."""
from sqlalchemy.orm import Session
from backend.app.models.user import User
from backend.app.models.workspace import Workspace
from backend.app.models.conversation import Conversation, Message
from backend.app.memory.manager import MemoryManager


def create_user_and_workspace(db: Session):
    user = User(
        email="test_mem@corp.com",
        hashed_password="hash",
        full_name="Mem User",
        role="engineer"
    )
    db.add(user)
    db.flush()
    ws = Workspace(
        name="Mem Workspace",
        slug=f"mem-ws-{user.id[:6]}",
        owner_id=user.id
    )
    db.add(ws)
    db.flush()
    return user, ws


def test_memory_sliding_window(db_session: Session):
    user, ws = create_user_and_workspace(db_session)
    conv = Conversation(
        workspace_id=ws.id,
        user_id=user.id,
        title="Test Conversation",
    )
    db_session.add(conv)
    db_session.flush()

    # Add 10 messages
    for i in range(10):
        role = "user" if i % 2 == 0 else "assistant"
        msg = Message(
            conversation_id=conv.id,
            role=role,
            content=f"Message {i}",
        )
        db_session.add(msg)
    db_session.commit()

    memory = MemoryManager(max_turns=3)  # 3 turns = 6 messages
    context = memory.get_context_messages(conv.id, db_session)
    assert len(context) == 6
    assert context[-1].content == "Message 9"


def test_reformulate_query_with_pronouns(db_session: Session):
    user, ws = create_user_and_workspace(db_session)
    conv = Conversation(
        workspace_id=ws.id,
        user_id=user.id,
        title="Incident Chat",
    )
    db_session.add(conv)
    db_session.flush()

    msg = Message(
        conversation_id=conv.id,
        role="user",
        content="Tell me about Incident 104 and database pool outage",
    )
    db_session.add(msg)
    db_session.commit()

    memory = MemoryManager()
    rewritten = memory.reformulate_query("What was its resolution?", conv.id, db_session)
    assert "Incident 104" in rewritten or "incident 104" in rewritten.lower()
