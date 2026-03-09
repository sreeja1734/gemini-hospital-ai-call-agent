"""
Gemini Hospital AI Call Agent — FastAPI Backend Server
Main entry point: registers all routers, middleware, startup/shutdown hooks.
"""
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from database.connection import init_db
from .routes.calls import router as calls_router
from .routes.appointments import router as appointments_router
from .routes.dashboard import router as dashboard_router
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

# ── CORS middleware (allow dashboard frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.run.app", "*"],
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
app.include_router(calls_router)
app.include_router(appointments_router)
app.include_router(dashboard_router)


# ── Health & status endpoints
@app.get("/health", tags=["System"])
async def health_check():
    """Health check for Cloud Run liveness probe."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "active_calls": conversation_manager.active_count()
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
