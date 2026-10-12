"""FastAPI application entrypoint for api-fuzzer-alan-vo."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.app.api.routes_auth import router as auth_router
from backend.app.api.routes_evaluation import router as eval_router
from backend.app.api.routes_jobs import router as jobs_router
from backend.app.api.routes_specs import router as specs_router
from backend.app.api.routes_stats import router as stats_router
from backend.app.core.config import get_settings
from backend.app.core.database import get_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager initializing database and verifying production safety."""
    settings = get_settings()
    settings.validate_production()
    db = get_db()
    db.init_db()
    yield


def create_app() -> FastAPI:
    """Factory creating configured FastAPI instance."""
    settings = get_settings()

    app = FastAPI(
        title="api-fuzzer-alan-vo",
        description="AI-powered adversarial API fuzzer with OpenAPI ingestion, deterministic mutations, and severity scoring",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS configuration allowing local UI dev and container routing
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routers
    app.include_router(auth_router)
    app.include_router(specs_router)
    app.include_router(jobs_router)
    app.include_router(stats_router)
    app.include_router(eval_router)

    @app.get("/api/health")
    def health_check() -> Dict[str, str]:
        """Liveness and health check endpoint."""
        return {
            "status": "ok",
            "version": "1.0.0",
            "app": settings.app_name,
            "env": settings.app_env,
            "demo_mode": str(settings.demo_mode).lower(),
        }

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Sanitizing error handler to prevent internal tracebacks or token leakage."""
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred while processing the request."}
        )

    return app


app = create_app()
