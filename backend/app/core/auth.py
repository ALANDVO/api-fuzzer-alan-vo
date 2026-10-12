"""Authentication & Authorization module supporting OIDC JWT bearer tokens and secure local demo mode."""
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from backend.app.core.config import get_settings

security_bearer = HTTPBearer(auto_error=False)

ROLE_HIERARCHY = {
    "admin": ["admin", "operator", "viewer"],
    "operator": ["operator", "viewer"],
    "viewer": ["viewer"]
}


class TokenUser(BaseModel):
    user_id: str
    email: str
    roles: List[str]
    auth_method: str = "bearer"

    def has_role(self, required_role: str) -> bool:
        for r in self.roles:
            if required_role in ROLE_HIERARCHY.get(r, []):
                return True
        return False


def create_access_token(user_id: str, email: str, roles: List[str], expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT access token for authentication."""
    settings = get_settings()
    delta = expires_delta or timedelta(minutes=settings.jwt_expiration_minutes)
    expire = datetime.now(timezone.utc) + delta
    payload = {
        "sub": user_id,
        "email": email,
        "roles": roles,
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "iss": settings.oidc_issuer_url or f"https://{settings.host}:{settings.port}",
        "aud": settings.oidc_audience,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Dict[str, any]:
    """Verify and decode a JWT bearer token."""
    settings = get_settings()
    try:
        # In demo or local secret mode, verify with HMAC secret
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=settings.oidc_audience,
            options={"verify_aud": bool(settings.oidc_audience), "verify_exp": True}
        )
        return payload
    except JWTError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired authorization token: {str(err)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)) -> TokenUser:
    """FastAPI dependency to extract and validate the authenticated user."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials)
    user_id = payload.get("sub")
    email = payload.get("email", "unknown@example.com")
    roles = payload.get("roles", ["viewer"])
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenUser(user_id=user_id, email=email, roles=roles)


def require_role(required_role: str):
    """Dependency factory checking that the current user has the required role."""
    def role_checker(user: TokenUser = Depends(get_current_user)) -> TokenUser:
        if not user.has_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: role '{required_role}' or higher required",
            )
        return user
    return role_checker
