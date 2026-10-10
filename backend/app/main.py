from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.artifacts import router as artifacts_router
from app.api.health import router as health_router
from app.api.ingest import router as ingest_router
from app.api.messages import router as messages_router
from app.api.search import router as search_router
from app.api.sessions import router as sessions_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.core.middleware import ClientIdMiddleware, RequestContextMiddleware
from app.db.session import SessionLocal, engine
from app.services.ingestion import IngestRunner


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging(settings.log_level)
    runner = IngestRunner(SessionLocal, settings)
    app.state.ingest_runner = runner
    if settings.ingest_on_startup:
        # Background task: the API answers /health immediately while ingestion runs.
        runner.start("startup")
    yield
    await runner.shutdown()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)
    application = FastAPI(title=settings.app_name, lifespan=lifespan)
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(ClientIdMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    register_error_handlers(application)
    application.include_router(health_router)
    application.include_router(sessions_router)
    application.include_router(messages_router)
    application.include_router(artifacts_router)
    application.include_router(ingest_router)
    application.include_router(search_router)
    return application


app = create_app()
