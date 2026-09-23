"""FastAPI application entry point for TigerGraph Agentic Fraud Investigation."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.utils.logging import get_logger, setup_logging
from backend.app.utils.time import now_iso

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan setup and teardown."""
    settings = get_settings()
    setup_logging(level=settings.LOG_LEVEL)
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


def create_app() -> FastAPI:
    """Application factory for FastAPI."""
    settings = get_settings()
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    # Enable CORS for local frontend development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from backend.app.api.routes import (
        benchmark_router,
        cases_router,
        investigations_router,
        mock_router,
    )

    # Register API routers
    app.include_router(investigations_router, prefix="/api/investigations", tags=["Investigations"])
    app.include_router(cases_router, prefix="/api/cases", tags=["Cases"])
    app.include_router(mock_router, prefix="/api/mock", tags=["Mock Actions"])
    app.include_router(benchmark_router, prefix="/api/benchmark", tags=["Benchmark"])

    @app.get("/health", tags=["Health"])
    async def health_check() -> Dict[str, str]:
        """Health check endpoint confirming application is running."""
        return {
            "status": "healthy",
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "timestamp": now_iso(),
        }

    @app.get("/", tags=["Root"])
    async def root() -> Dict[str, str]:
        """Root endpoint returning basic system information."""
        return {
            "message": f"Welcome to {settings.APP_NAME}",
            "health_url": "/health",
            "docs_url": "/docs",
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
