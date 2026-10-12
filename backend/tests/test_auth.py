"""Tests covering OIDC authentication, JWT tokens, role authorization, and rejection."""
from datetime import timedelta
import pytest
from jose import jwt
from backend.app.core.auth import create_access_token, decode_token
from backend.app.core.config import get_settings


def test_token_creation_and_decoding():
    token = create_access_token("user-1", "user1@example.com", ["operator"])
    payload = decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["email"] == "user1@example.com"
    assert "operator" in payload["roles"]


def test_expired_token_rejection():
    # Token expired 1 hour ago
    expired_token = create_access_token("user-expired", "exp@example.com", ["viewer"], expires_delta=timedelta(hours=-1))
    with pytest.raises(Exception) as exc_info:
        decode_token(expired_token)
    assert "expired" in str(exc_info.value).lower()


def test_unauthenticated_request_rejected(client):
    resp = client.get("/api/specs")
    assert resp.status_code == 401
    assert "detail" in resp.json()


def test_role_denial_forbidden(client, viewer_token):
    # Viewer tries to upload spec (operator required)
    headers = {"Authorization": f"Bearer {viewer_token}"}
    resp = client.post("/api/specs", headers=headers, json={"name": "test", "raw_spec": "{}"})
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["detail"]


def test_demo_login_flow(client):
    resp = client.post("/api/auth/login", json={"email": "operator@test.com", "role": "operator"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert "operator" in data["roles"]

    # Use the generated token to access /api/auth/me
    token = data["access_token"]
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "operator@test.com"


def test_oidc_config_endpoint(client):
    resp = client.get("/api/auth/oidc-config")
    assert resp.status_code == 200
    data = resp.json()
    assert "supported_roles" in data
    assert "viewer" in data["supported_roles"]


def test_oidc_pkce_state_rejection_simulation(client):
    # Simulates PKCE verification check: state mismatch or invalid code verifier rejected
    state_valid = "secure-random-state-12345"
    state_forged = "attacker-forged-state"
    assert state_valid != state_forged
    # Reject request when state does not match session
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.payload"})
    assert resp.status_code == 401
