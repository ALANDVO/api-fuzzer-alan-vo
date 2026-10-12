"""Pytest fixtures for backend testing."""
import os
import tempfile
import pytest
from fastapi.testclient import TestClient

# Ensure test runs in development/demo mode with isolated SQLite
os.environ["APP_ENV"] = "development"
os.environ["DEMO_MODE"] = "true"
os.environ["JWT_SECRET"] = "test-secret-key-for-unit-testing-32b"
os.environ["DATABASE_PATH"] = ":memory:"

from backend.app.core.auth import create_access_token
from backend.app.core.database import Database, get_db
from backend.app.main import create_app


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Provide isolated in-memory SQLite database for each test run."""
    test_db = Database(":memory:")
    import backend.app.core.database as db_mod
    monkeypatch.setattr(db_mod, "_db_instance", test_db)
    return test_db


@pytest.fixture
def client():
    """Test client for FastAPI HTTP endpoints."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def viewer_token():
    return create_access_token("test-viewer", "viewer@example.com", ["viewer"])


@pytest.fixture
def operator_token():
    return create_access_token("test-operator", "operator@example.com", ["operator"])


@pytest.fixture
def admin_token():
    return create_access_token("test-admin", "admin@example.com", ["admin"])
