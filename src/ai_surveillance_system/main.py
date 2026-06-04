from contextlib import asynccontextmanager
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ai_surveillance_system.core.config import get_settings
from ai_surveillance_system.core.logger import get_logger
from ai_surveillance_system.api.routes import upload, stream, detections

settings = get_settings()
logger = get_logger(__name__)


# Dependency health state (updated during lifespan)
health_state: dict = {
    "db": "not_initialized",
    "redis": "not_initialized",
}


# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # TODO Step 2: Initialize DB connection pool here

    # TODO Step 4: Initialize Redis here

    yield

    logger.info("Shutting down ...")

    # TODO Step 2: Close DB connection pool here

    # TODO Step 4: Close Redis connection here


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
            "http://localhost:3000",
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
    # upload.router      → prefix /api/v1  → POST /api/v1/upload
    # stream.router      → no prefix       → WS   /ws/stream
    # detections.router  → prefix /api/v1  → GET  /api/v1/detections[/{id}]
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
