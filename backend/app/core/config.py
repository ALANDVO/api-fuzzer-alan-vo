"""Configuration settings for api-fuzzer-alan-vo."""
import os
from typing import Optional
from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = "api-fuzzer-alan-vo"
    app_version: str = "1.0.0"
    app_env: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development").lower())
    demo_mode: bool = Field(default_factory=lambda: os.getenv("DEMO_MODE", "true").lower() in ("true", "1", "yes"))
    host: str = Field(default_factory=lambda: os.getenv("HOST", "127.0.0.1"))
    port: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))

    # Security & OIDC settings
    jwt_secret: str = Field(default_factory=lambda: os.getenv("JWT_SECRET", "dev-secret-key-must-change-in-production-32b"))
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 120
    oidc_issuer_url: Optional[str] = Field(default_factory=lambda: os.getenv("OIDC_ISSUER_URL"))
    oidc_client_id: str = Field(default_factory=lambda: os.getenv("OIDC_CLIENT_ID", "api-fuzzer-app"))
    oidc_audience: str = Field(default_factory=lambda: os.getenv("OIDC_AUDIENCE", "api-fuzzer-app"))

    # Database
    database_path: str = Field(default_factory=lambda: os.getenv("DATABASE_PATH", "./data/fuzzer.db"))

    # Multi-provider LLM Configuration (Key is only secret variable)
    llm_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("LLM_API_KEY"))
    llm_provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai").lower())
    llm_model: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o"))
    llm_base_url: Optional[str] = Field(default_factory=lambda: os.getenv("LLM_BASE_URL"))
    llm_timeout_seconds: float = Field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0")))

    def validate_production(self) -> None:
        """Enforce strict production invariants as mandated by security contract."""
        if self.app_env == "production":
            if self.demo_mode:
                raise ValueError("Security violation: Demo mode is strictly forbidden in production environment.")
            if not self.oidc_issuer_url and self.jwt_secret.startswith("dev-secret"):
                raise ValueError("Security violation: Production deployment requires external OIDC or configured non-default JWT secret.")


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.validate_production()
    return _settings
