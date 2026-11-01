"""Pytest fixtures and configuration."""
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.db.session import Base, get_db
from backend.app.core.config import settings

# Force offline/test modes during test execution
settings.USE_FAKE_LLM = True
settings.USE_FAKE_EMBEDDINGS = True

# Override test-specific settings
settings.CORS_ORIGINS = []
settings.PRIMARY_LLM_PROVIDER = "anthropic"
settings.PRIMARY_LLM_MODEL = "claude-3-5-sonnet-20241022"
settings.FALLBACK_LLM_PROVIDER = "openai"
settings.FALLBACK_LLM_MODEL = "gpt-4o"
settings.SECRET_KEY = "dev-insecure-change-in-production-min-32-chars"
settings.ENVIRONMENT = "test"

# Disable rate limiting for tests
settings.RATE_LIMIT_AUTH = 1000
settings.RATE_LIMIT_AUTH_WINDOW = 1
settings.RATE_LIMIT_UPLOAD = 1000
settings.RATE_LIMIT_UPLOAD_WINDOW = 1
settings.RATE_LIMIT_GENERAL = 10000
settings.RATE_LIMIT_GENERAL_WINDOW = 1

# Create in-memory SQLite database for fast isolated unit and integration tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Provide a clean isolated database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provide a TestClient connected to the isolated test database."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(client: TestClient) -> dict:
    """Register and return a test user credentials & profile."""
    user_payload = {
        "email": "engineer@enterprise.io",
        "password": "Password123!",
        "full_name": "Test Senior Engineer",
        "role": "engineer",
    }
    response = client.post("/api/v1/auth/register", json=user_payload)
    assert response.status_code == 201, response.text
    user_data = response.json()
    user_data["plain_password"] = user_payload["password"]
    return user_data


@pytest.fixture(scope="function")
def auth_headers(client: TestClient, test_user: dict) -> dict:
    """Return valid Authorization Bearer headers for the test user."""
    login_payload = {
        "email": test_user["email"],
        "password": test_user["plain_password"],
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

