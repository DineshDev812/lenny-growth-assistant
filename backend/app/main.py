from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.messages import router as messages_router
from app.api.sessions import router as sessions_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.core.middleware import ClientIdMiddleware, RequestContextMiddleware
from app.db.session import engine


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging(get_settings().log_level)
    yield
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
    return application


app = create_app()
