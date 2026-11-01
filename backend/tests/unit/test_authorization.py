"""Authorization tests for conversation and agent access control.

These tests verify that users can only access their own conversations and agent runs,
even within the same workspace.
"""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.app.models.user import User
from backend.app.models.workspace import Workspace, WorkspaceMember
from backend.app.core.security import hash_password


def get_default_workspace_id(client: TestClient, auth_headers: dict) -> str:
    """Helper to fetch the ID of the user's default workspace."""
    response = client.get("/api/v1/workspaces", headers=auth_headers)
    assert response.status_code == 200
    workspaces = response.json()
    assert len(workspaces) > 0
    return workspaces[0]["id"]


def create_user_in_workspace(db: Session, workspace_id: str, email: str, password: str, full_name: str) -> User:
    """Create a user and add them as a member to the given workspace."""
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role="engineer",
        is_active=True,
    )
    db.add(user)
    db.flush()
    
    member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=user.id,
        role="member",
    )
    db.add(member)
    db.commit()
    db.refresh(user)
    return user


def get_auth_headers(client: TestClient, email: str, password: str) -> dict:
    """Get auth headers for a user."""
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200
    return {"Authorization": f"Bearer {login_resp.json()['access_token']}"}


def test_conversation_list_only_own_conversations(client: TestClient, test_user: dict, auth_headers: dict, db_session: Session):
    """Test that list_conversations only returns user's own conversations."""
    workspace_id = get_default_workspace_id(client, auth_headers)
    
    # Create a conversation for test_user
    chat_payload = {
        "query": "Test conversation for user 1",
        "workspace_id": workspace_id,
    }
    chat_resp = client.post(
        f"/api/v1/workspaces/{workspace_id}/chat",
        headers=auth_headers,
        json=chat_payload,
    )
    assert chat_resp.status_code == 200
    conv_id_1 = chat_resp.json()["conversation_id"]
    
    # List conversations - should see the one we created
    list_resp = client.get(
        f"/api/v1/workspaces/{workspace_id}/conversations",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200
    conversations = list_resp.json()
    assert len(conversations) >= 1
    assert any(c["id"] == conv_id_1 for c in conversations)
    
    # Create a second user in the same workspace
    user2 = create_user_in_workspace(db_session, workspace_id, "user2@company.com", "Password123!", "User Two")
    
    # Login as user2
    user2_headers = get_auth_headers(client, "user2@company.com", "Password123!")
    
    # User2 should have access to the workspace but should not see user1's conversations
    list_resp2 = client.get(
        f"/api/v1/workspaces/{workspace_id}/conversations",
        headers=user2_headers,
    )
    assert list_resp2.status_code == 200
    conversations2 = list_resp2.json()
    # User2 should not see user1's conversation
    assert not any(c["id"] == conv_id_1 for c in conversations2)


def test_get_conversation_denied_for_other_user(client: TestClient, test_user: dict, auth_headers: dict, db_session: Session):
    """Test that get_conversation returns 404 for other user's conversation."""
    workspace_id = get_default_workspace_id(client, auth_headers)
    
    # Create a conversation for test_user
    chat_payload = {
        "query": "Test conversation for user 1",
        "workspace_id": workspace_id,
    }
    chat_resp = client.post(
        f"/api/v1/workspaces/{workspace_id}/chat",
        headers=auth_headers,
        json=chat_payload,
    )
    assert chat_resp.status_code == 200
    conv_id = chat_resp.json()["conversation_id"]
    
    # Create a second user in the same workspace
    user2 = create_user_in_workspace(db_session, workspace_id, "user2@company.com", "Password123!", "User Two")
    
    # Login as user2
    user2_headers = get_auth_headers(client, "user2@company.com", "Password123!")
    
    # User2 tries to access user1's conversation
    get_resp = client.get(
        f"/api/v1/workspaces/{workspace_id}/conversations/{conv_id}",
        headers=user2_headers,
    )
    assert get_resp.status_code == 404
    assert "not found" in get_resp.json()["detail"].lower()


def test_delete_conversation_denied_for_other_user(client: TestClient, test_user: dict, auth_headers: dict, db_session: Session):
    """Test that delete_conversation returns 404 for other user's conversation."""
    workspace_id = get_default_workspace_id(client, auth_headers)
    
    # Create a conversation for test_user
    chat_payload = {
        "query": "Test conversation for user 1",
        "workspace_id": workspace_id,
    }
    chat_resp = client.post(
        f"/api/v1/workspaces/{workspace_id}/chat",
        headers=auth_headers,
        json=chat_payload,
    )
    assert chat_resp.status_code == 200
    conv_id = chat_resp.json()["conversation_id"]
    
    # Create a second user in the same workspace
    user2 = create_user_in_workspace(db_session, workspace_id, "user2@company.com", "Password123!", "User Two")
    
    # Login as user2
    user2_headers = get_auth_headers(client, "user2@company.com", "Password123!")
    
    # User2 tries to delete user1's conversation
    del_resp = client.delete(
        f"/api/v1/workspaces/{workspace_id}/conversations/{conv_id}",
        headers=user2_headers,
    )
    assert del_resp.status_code == 404
    assert "not found" in del_resp.json()["detail"].lower()


def test_agent_run_list_only_own_runs(client: TestClient, test_user: dict, auth_headers: dict, db_session: Session):
    """Test that list_agent_runs only returns user's own runs."""
    workspace_id = get_default_workspace_id(client, auth_headers)
    
    # Create an agent run for test_user
    agent_payload = {
        "task": "Test investigation for user 1",
        "workspace_id": workspace_id,
        "max_steps": 2,
    }
    agent_resp = client.post(
        f"/api/v1/workspaces/{workspace_id}/agent/investigate",
        headers=auth_headers,
        json=agent_payload,
    )
    assert agent_resp.status_code == 201
    run_id_1 = agent_resp.json()["id"]
    
    # List agent runs - should see the one we created
    list_resp = client.get(
        f"/api/v1/workspaces/{workspace_id}/agent/runs",
        headers=auth_headers,
    )
    assert list_resp.status_code == 200
    runs = list_resp.json()
    assert len(runs) >= 1
    assert any(r["id"] == run_id_1 for r in runs)
    
    # Create a second user in the same workspace
    user2 = create_user_in_workspace(db_session, workspace_id, "user2@company.com", "Password123!", "User Two")
    
    # Login as user2
    user2_headers = get_auth_headers(client, "user2@company.com", "Password123!")
    
    # User2 should not see user1's agent runs
    list_resp2 = client.get(
        f"/api/v1/workspaces/{workspace_id}/agent/runs",
        headers=user2_headers,
    )
    assert list_resp2.status_code == 200
    runs2 = list_resp2.json()
    assert not any(r["id"] == run_id_1 for r in runs2)


def test_get_agent_run_denied_for_other_user(client: TestClient, test_user: dict, auth_headers: dict, db_session: Session):
    """Test that get_agent_run returns 404 for other user's run."""
    workspace_id = get_default_workspace_id(client, auth_headers)
    
    # Create an agent run for test_user
    agent_payload = {
        "task": "Test investigation for user 1",
        "workspace_id": workspace_id,
        "max_steps": 2,
    }
    agent_resp = client.post(
        f"/api/v1/workspaces/{workspace_id}/agent/investigate",
        headers=auth_headers,
        json=agent_payload,
    )
    assert agent_resp.status_code == 201
    run_id = agent_resp.json()["id"]
    
    # Create a second user in the same workspace
    user2 = create_user_in_workspace(db_session, workspace_id, "user2@company.com", "Password123!", "User Two")
    
    # Login as user2
    user2_headers = get_auth_headers(client, "user2@company.com", "Password123!")
    
    # User2 tries to access user1's agent run
    get_resp = client.get(
        f"/api/v1/workspaces/{workspace_id}/agent/runs/{run_id}",
        headers=user2_headers,
    )
    assert get_resp.status_code == 404
    assert "not found" in get_resp.json()["detail"].lower()


def test_rag_chat_denied_for_other_user_conversation(client: TestClient, test_user: dict, auth_headers: dict, db_session: Session):
    """Test that chat endpoint denies access to other user's conversation."""
    workspace_id = get_default_workspace_id(client, auth_headers)
    
    # Create a conversation for test_user
    chat_payload = {
        "query": "Test conversation for user 1",
        "workspace_id": workspace_id,
    }
    chat_resp = client.post(
        f"/api/v1/workspaces/{workspace_id}/chat",
        headers=auth_headers,
        json=chat_payload,
    )
    assert chat_resp.status_code == 200
    conv_id = chat_resp.json()["conversation_id"]
    
    # Create a second user in the same workspace
    user2 = create_user_in_workspace(db_session, workspace_id, "user2@company.com", "Password123!", "User Two")
    
    # Login as user2
    user2_headers = get_auth_headers(client, "user2@company.com", "Password123!")
    
    # User2 tries to continue user1's conversation
    chat_payload2 = {
        "query": "Follow up question",
        "workspace_id": workspace_id,
        "conversation_id": conv_id,
    }
    chat_resp2 = client.post(
        f"/api/v1/workspaces/{workspace_id}/chat",
        headers=user2_headers,
        json=chat_payload2,
    )
    # Should get 400 (EntityNotFoundError) because conversation not found for user2
    assert chat_resp2.status_code == 400
    error_data = chat_resp2.json()
    # EIPException handler returns {error, message, details}
    assert "message" in error_data or "detail" in error_data
    msg = error_data.get("message", error_data.get("detail", ""))
    assert "not found" in msg.lower()