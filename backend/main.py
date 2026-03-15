"""
Gemini Hospital AI Call Agent — FastAPI Backend Server
Main entry point: registers all routers, middleware, startup/shutdown hooks.
"""
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .config import settings
from database.connection import init_db
from .routes.calls import router as calls_router
from .routes.appointments import router as appointments_router
from .routes.dashboard import router as dashboard_router
from .routes.vapi import router as vapi_router
from .routes.auth import router as auth_router
from .auth import get_current_user
from ai.conversation_manager import conversation_manager

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Starting Gemini Hospital AI Call Agent", version=settings.APP_VERSION)
    await init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    active = conversation_manager.active_count()
    if active:
        logger.warning("Shutting down with active calls", count=active)
    logger.info("Gemini Hospital AI Call Agent shut down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI-powered hospital call agent using Google Gemini Live API. "
        "Handles appointment booking, emergency detection, and real-time conversations."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# ── Rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS middleware (allow dashboard frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


# ── Routers
app.include_router(auth_router)
app.include_router(calls_router)
app.include_router(appointments_router)
app.include_router(dashboard_router)
app.include_router(vapi_router, prefix="/vapi")


# ── Health & status endpoints
@app.get("/health", tags=["System"])
async def health_check():
    """Health check for Cloud Run liveness probe. Verifies DB connectivity."""
    db_ok = False
    try:
        from database.connection import async_engine
        from sqlalchemy import text
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
        "supported_languages": settings.SUPPORTED_LANGUAGES
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
