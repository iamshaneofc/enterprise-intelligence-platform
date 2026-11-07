"""Unit tests for document ingestion, parsing, chunking, and deduplication."""
import io
from fastapi.testclient import TestClient


def get_default_workspace_id(client: TestClient, auth_headers: dict) -> str:
    """Helper to fetch the ID of the user's default workspace."""
    response = client.get("/api/v1/workspaces", headers=auth_headers)
    assert response.status_code == 200
    workspaces = response.json()
    assert len(workspaces) > 0
    return workspaces[0]["id"]


def test_upload_markdown_document(client: TestClient, auth_headers: dict):
    ws_id = get_default_workspace_id(client, auth_headers)
    
    md_content = b"""# Incident 104 Postmortem
## Summary
On 2026-03-15 at 14:22 UTC, the PostgreSQL connection pool exhausted all 200 connections.
The root cause was a missing index on the accounts query combined with a transaction leak.

## Resolution
The connection timeout was lowered from 60s to 5s, and max_connections was bumped to 400.
    """
    
    files = {"file": ("incident_104.md", io.BytesIO(md_content), "text/markdown")}
    response = client.post(
        f"/api/v1/workspaces/{ws_id}/documents/upload",
        headers=auth_headers,
        files=files,
    )
    assert response.status_code == 201
    data = response.json()
    assert "document" in data
    doc = data["document"]
    assert doc["title"] == "incident_104"
    assert doc["status"] == "completed"
    assert doc["chunk_count"] > 0
    assert doc["file_type"] == "md"


def test_upload_duplicate_document_returns_existing(client: TestClient, auth_headers: dict):
    ws_id = get_default_workspace_id(client, auth_headers)
    content = b"# Architecture Runbook\n\nAll services require health check probes at /health."
    
    # First upload
    files1 = {"file": ("runbook.md", io.BytesIO(content), "text/markdown")}
    resp1 = client.post(
        f"/api/v1/workspaces/{ws_id}/documents/upload",
        headers=auth_headers,
        files=files1,
    )
    assert resp1.status_code == 201
    doc1 = resp1.json()["document"]

    # Second upload with identical content
    files2 = {"file": ("runbook_duplicate.md", io.BytesIO(content), "text/markdown")}
    resp2 = client.post(
        f"/api/v1/workspaces/{ws_id}/documents/upload",
        headers=auth_headers,
        files=files2,
    )
    assert resp2.status_code == 201
    doc2 = resp2.json()["document"]
    # Should identify duplicate hash and return doc1 ID
    assert doc1["id"] == doc2["id"]


def test_get_document_chunks(client: TestClient, auth_headers: dict):
    ws_id = get_default_workspace_id(client, auth_headers)
    content = b"Database connection configuration parameters and guidelines for high availability."
    
    files = {"file": ("db_guide.txt", io.BytesIO(content), "text/plain")}
    upload_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/documents/upload",
        headers=auth_headers,
        files=files,
    )
    doc_id = upload_resp.json()["document"]["id"]

    chunks_resp = client.get(
        f"/api/v1/workspaces/{ws_id}/documents/{doc_id}/chunks",
        headers=auth_headers,
    )
    assert chunks_resp.status_code == 200
    chunks = chunks_resp.json()
    assert len(chunks) >= 1
    assert "content" in chunks[0]
    assert chunks[0]["chunk_index"] == 0


def test_download_document(client: TestClient, auth_headers: dict):
    ws_id = get_default_workspace_id(client, auth_headers)
    content = b"# Architecture Download Test\n\nOriginal file persistence verification."

    files = {"file": ("download_test.md", io.BytesIO(content), "text/markdown")}
    upload_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/documents/upload",
        headers=auth_headers,
        files=files,
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["document"]["id"]

    download_resp = client.get(
        f"/api/v1/workspaces/{ws_id}/documents/{doc_id}/download",
        headers=auth_headers,
    )
    assert download_resp.status_code == 200
    assert download_resp.content == content
    assert "attachment" in download_resp.headers.get("content-disposition", "")
    assert "download_test.md" in download_resp.headers.get("content-disposition", "")


def test_delete_document(client: TestClient, auth_headers: dict):
    ws_id = get_default_workspace_id(client, auth_headers)
    content = b"Temporary document to be deleted."
    
    files = {"file": ("temp.txt", io.BytesIO(content), "text/plain")}
    upload_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/documents/upload",
        headers=auth_headers,
        files=files,
    )
    doc_id = upload_resp.json()["document"]["id"]

    del_resp = client.delete(
        f"/api/v1/workspaces/{ws_id}/documents/{doc_id}",
        headers=auth_headers,
    )
    assert del_resp.status_code == 204

    # Verify document is gone
    get_resp = client.get(
        f"/api/v1/workspaces/{ws_id}/documents/{doc_id}",
        headers=auth_headers,
    )
    assert get_resp.status_code == 400 or get_resp.status_code == 404

