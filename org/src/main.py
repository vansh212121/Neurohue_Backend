from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from typing import Dict, Any
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import settings
from src.core.exception_handler import register_exception_handlers
from src.db.session import db
from src.db.redis_conn import redis_client_instance
from src.utils.deps import get_health_status
from src.db import base
from src.api.v1.endpoints import user, region


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events.
    Connects to the database and redis.
    """
    await db.connect()
    await redis_client_instance.connect()
    yield
    await redis_client_instance.disconnect()
    await db.disconnect()


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=settings.DESCRIPTION,
        lifespan=lifespan,
    )

    register_exception_handlers(app)

    app.include_router(user.router)
    app.include_router(region.router)

    app.add_middleware(
        CORSMiddleware,
        # allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = create_application()


@app.get("/health", response_model=Dict[str, Any])
async def health_check(health: Dict[str, Any] = Depends(get_health_status)):
    """
    Health check endpoint that provides status and version info.
    """
    return health
