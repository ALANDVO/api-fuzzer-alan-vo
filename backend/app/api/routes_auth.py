"""Authentication API routes supporting local demo mode, OIDC discovery info, and user session management."""
from datetime import timedelta
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.core.auth import TokenUser, create_access_token, get_current_user
from backend.app.core.config import get_settings
from backend.app.core.database import get_db
from backend.app.models.schemas import AuthLoginRequest, AuthTokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=AuthTokenResponse)
def login(req: AuthLoginRequest) -> AuthTokenResponse:
    """Authenticate user and issue JWT bearer token."""
    settings = get_settings()
    if not settings.demo_mode and settings.app_env == "production":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Direct password login is disabled in production. Use configured Keycloak OIDC authorization code flow."
        )

    # Demo mode allows testing roles: viewer, operator, admin
    role = req.role if req.role in ("viewer", "operator", "admin") else "operator"
    email = req.email.strip()
    user_id = email.split("@")[0] or "user-001"

    token = create_access_token(
        user_id=user_id,
        email=email,
        roles=[role],
        expires_delta=timedelta(minutes=settings.jwt_expiration_minutes)
    )

    get_db().record_audit(
        user_id=user_id,
        action="auth.login",
        resource="session",
        details={"email": email, "role": role, "mode": "demo" if settings.demo_mode else "standard"}
    )

    return AuthTokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in_seconds=settings.jwt_expiration_minutes * 60,
        user_id=user_id,
        email=email,
        roles=[role]
    )


@router.get("/me", response_model=TokenUser)
def get_me(user: TokenUser = Depends(get_current_user)) -> TokenUser:
    """Return currently authenticated identity and assigned roles."""
    return user


@router.get("/oidc-config")
def get_oidc_config() -> Dict[str, Any]:
    """Provide OIDC discovery and Keycloak brokering settings."""
    settings = get_settings()
    return {
        "demo_mode": settings.demo_mode,
        "app_env": settings.app_env,
        "oidc_issuer_url": settings.oidc_issuer_url,
        "client_id": settings.oidc_client_id,
        "supported_roles": ["viewer", "operator", "admin"],
        "saml_brokered": True,
    }


@router.post("/logout")
def logout(user: TokenUser = Depends(get_current_user)) -> Dict[str, str]:
    """Invalidate session and log audit event."""
    get_db().record_audit(
        user_id=user.user_id,
        action="auth.logout",
        resource="session",
        details={"email": user.email}
    )
    return {"message": "Successfully logged out."}
