"""Unit tests for user registration, authentication, and JWT tokens."""
from fastapi.testclient import TestClient


def test_user_registration(client: TestClient):
    payload = {
        "email": "dev1@company.com",
        "password": "SecurePassword123!",
        "full_name": "Dev One",
        "role": "engineer"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "dev1@company.com"
    assert data["full_name"] == "Dev One"
    assert data["role"] == "engineer"
    assert data["is_active"] is True
    assert "id" in data


def test_user_duplicate_registration_fails(client: TestClient, test_user: dict):
    payload = {
        "email": test_user["email"],
        "password": "AnotherPassword456!",
        "full_name": "Duplicate User",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_user_login_success(client: TestClient, test_user: dict):
    payload = {
        "email": test_user["email"],
        "password": test_user["plain_password"],
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_user_login_invalid_password(client: TestClient, test_user: dict):
    payload = {
        "email": test_user["email"],
        "password": "WrongPassword999!",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_get_current_user_profile(client: TestClient, auth_headers: dict, test_user: dict):
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user["id"]
    assert data["email"] == test_user["email"]


def test_unauthenticated_request_rejected(client: TestClient):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401

