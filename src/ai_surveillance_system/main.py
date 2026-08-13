from contextlib import asynccontextmanager
import time

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ai_surveillance_system.core.config import get_settings
from ai_surveillance_system.core.logger import get_logger
from ai_surveillance_system.db.session import init_db, close_db
from ai_surveillance_system.ml.model_loader import model_loader
from ai_surveillance_system.api.routes import upload, stream, detections, auth

settings = get_settings()
logger = get_logger(__name__)


# Dependency health state (updated during lifespan)
health_state: dict = {
    "db": "not_initialized",
    "redis": "not_initialized",
    "model": "not_initialized",
}

# Shared Redis client used for health checks (Celery has its own separate connection)
redis_client: aioredis.Redis | None = None


# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client

    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Initialize DB
    try:
        await init_db()
        health_state["db"] = "ok"
    except Exception as exc:
        logger.error(f"Database initialization failed: {exc}", exc_info=True)
        health_state["db"] = "error"

    # Initialize Redis
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        health_state["redis"] = "ok"
        logger.info("Redis connection established")
    except Exception as exc:
        logger.error(f"Redis initialization failed: {exc}", exc_info=True)
        health_state["redis"] = "error"

    # Load the ML model into this process
    try:
        model_loader.load()
        health_state["model"] = "ok"
        logger.info("ML model loaded")
    except Exception as exc:
        logger.error(f"Model loading failed: {exc}", exc_info=True)
        health_state["model"] = "error"

    yield

    logger.info("Shutting down ...")

    # Close DB connection pool
    await close_db()

    # Close Redis connection
    if redis_client is not None:
        await redis_client.close()
        logger.info("Redis connection closed")


# App factory
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI-powered video surveillance system",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost",  # nginx-served frontend, port 80
            "http://localhost:8000",  # direct API access (dev/debug)
            "http://localhost:3000",  # local vite/react dev server
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request timing middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
        logger.debug(
            f"{request.method} {request.url.path} → {response.status_code} ({duration_ms:.1f}ms)"
        )
        return response

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            f"Unhandled exception on {request.url.path}: {exc}", exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Please try again later."},
        )

    # Register routers
    # auth.router → prefix /auth → POST /auth/register, /auth/login, /auth/refresh, GET /auth/me
    # upload.router → prefix /api/v1 → POST /api/v1/upload
    # stream.router → no prefix → WS   /ws/stream
    # detections.router → prefix /api/v1  → GET  /api/v1/detections[/{id}]
    app.include_router(auth.router)
    app.include_router(upload.router)
    app.include_router(stream.router)
    app.include_router(detections.router)

    # Health check
    @app.get("/health", tags=["System"])
    async def health_check():
        all_ok = all(v == "ok" for v in health_state.values())

        return JSONResponse(
            status_code=200 if all_ok else 503,
            content={
                "status": "healthy" if all_ok else "unhealthy",
                "version": settings.APP_VERSION,
                "environment": settings.ENVIRONMENT,
                "dependencies": health_state,
            },
        )

    return app


app = create_app()
