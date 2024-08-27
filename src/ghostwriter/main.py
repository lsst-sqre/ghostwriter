"""The main application factory for the ghostwriter service.

Notes
-----
Be aware that, following the normal pattern for FastAPI services, the app is
constructed when this module is loaded and is not deferred until a function is
called.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import metadata, version

import structlog
from fastapi import FastAPI
from safir.dependencies.http_client import http_client_dependency
from safir.logging import configure_logging, configure_uvicorn_logging
from safir.middleware.x_forwarded import XForwardedMiddleware
from safir.slack.webhook import SlackRouteErrorHandler

from .config import config
from .handlers.external import external_router
from .handlers.internal import internal_router

__all__ = ["app", "lifespan"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Set up and tear down the application."""
    # Any code here will be run when the application starts up.

    yield

    # Any code here will be run when the application shuts down.
    await http_client_dependency.aclose()


configure_logging(
    profile=config.profile,
    log_level=config.log_level,
    name="ghostwriter",
)
configure_uvicorn_logging(config.log_level)

app = FastAPI(
    title="ghostwriter",
    description=metadata("ghostwriter")["Summary"],
    version=version("ghostwriter"),
    openapi_url=f"{config.path_prefix}/openapi.json",
    docs_url=f"{config.path_prefix}/docs",
    redoc_url=f"{config.path_prefix}/redoc",
    lifespan=lifespan,
)
"""The main FastAPI application for ghostwriter."""

# Attach the routers.
app.include_router(internal_router)
app.include_router(external_router, prefix=f"{config.path_prefix}")

# Add middleware.
app.add_middleware(XForwardedMiddleware)

# Enable Slack alerting for uncaught exceptions.
if config.alert_hook:
    logger = structlog.get_logger("ghostwriter")
    SlackRouteErrorHandler.initialize(
        str(config.alert_hook), "ghostwriter", logger
    )
    logger.debug("Initialized Slack webhook")
