"""
Hospital AI Call Agent FastAPI backend server.
Main entry point: registers all routers, middleware, startup/shutdown hooks.
"""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from ai.conversation_manager import conversation_manager
from database.connection import init_db

from .config import settings
from .routes.appointments import router as appointments_router
from .routes.auth import router as auth_router
from .routes.calls import router as calls_router
from .routes.dashboard import router as dashboard_router
from .routes.voice import router as voice_router

logger = structlog.get_logger()

try:
    from .agents.hospital_agent import hospital_receptionist_agent
except ImportError as exc:
    logger.warning("Hospital receptionist ADK agent module import failed", error=str(exc))
    hospital_receptionist_agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    logger.info("Starting Hospital AI Call Agent", version=settings.APP_VERSION)
    if hospital_receptionist_agent:
        logger.info(
            "Hospital receptionist ADK agent loaded successfully",
            agent_name=hospital_receptionist_agent.name,
        )
    else:
        logger.warning("Hospital receptionist ADK agent could not be loaded")

    await init_db()
    logger.info("Database initialized")
    yield

    active = conversation_manager.active_count()
    if active:
        logger.warning("Shutting down with active calls", count=active)
    logger.info("Hospital AI Call Agent shut down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI-powered hospital call agent using Google ADK with Gemini reasoning. "
        "Handles appointment booking, emergency detection, and real-time conversations."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


app.include_router(auth_router)
app.include_router(calls_router)
app.include_router(appointments_router)
app.include_router(dashboard_router)
app.include_router(voice_router)


@app.get("/health", tags=["System"])
async def health_check():
    """Health check for Cloud Run liveness probe. Verifies DB connectivity."""
    db_ok = False
    try:
        from sqlalchemy import text

        from database.connection import async_engine

        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    status = "healthy" if db_ok else "degraded"
    return {
        "status": status,
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "active_calls": conversation_manager.active_count(),
        "database": "connected" if db_ok else "unavailable",
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with system information."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "hospital": settings.HOSPITAL_NAME,
        "supported_languages": settings.SUPPORTED_LANGUAGES,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
