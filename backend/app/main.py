"""FastAPI application entrypoint for Enterprise Intelligence Platform."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.core.logging import setup_logging, logger
from backend.app.core.exceptions import EIPException
from backend.app.core.rate_limit import RateLimitMiddleware
from backend.app.db.session import init_db
from backend.app.api.routes import health, auth, workspaces, documents, chat, conversations, agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for application startup and shutdown."""
    setup_logging()
    logger.info("Initializing Enterprise Intelligence Platform backend...")
    init_db()
    logger.info("Database schemas initialized.")
    yield
    logger.info("Enterprise Intelligence Platform backend shutting down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise Intelligence Platform - Advanced Technical Document & Engineering AI Assistant",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiting middleware (added before CORS to catch all requests)
app.add_middleware(RateLimitMiddleware)

# CORS middleware - restrict origins in production
cors_origins = settings.CORS_ORIGINS
if settings.ENVIRONMENT == "production" and cors_origins == ["*"]:
    logger.warning("CORS_ORIGINS is set to ['*'] in production! This is insecure.")
    # In production, you should explicitly set allowed origins
    # cors_origins = ["https://your-frontend-domain.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)


@app.exception_handler(EIPException)
async def eip_exception_handler(request: Request, exc: EIPException):
    """Handle custom application exceptions."""
    logger.error(f"EIP Error: {exc.message} - Details: {exc.details}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
        },
    )


# Include Core routers
app.include_router(health.router)
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(workspaces.router, prefix=settings.API_V1_STR)
app.include_router(documents.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)
app.include_router(conversations.router, prefix=settings.API_V1_STR)
app.include_router(agent.router, prefix=settings.API_V1_STR)
