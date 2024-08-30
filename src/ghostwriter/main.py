"""The main application factory for the ghostwriter service."""

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import metadata, version

import structlog
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from safir.dependencies.http_client import http_client_dependency
from safir.fastapi import ClientRequestError, client_request_error_handler
from safir.logging import configure_logging, configure_uvicorn_logging
from safir.middleware.x_forwarded import XForwardedMiddleware
from safir.slack.webhook import SlackRouteErrorHandler

from .dependencies.config import config_dependency
from .dependencies.context import context_dependency
from .handlers.external import external_router
from .handlers.internal import internal_router

__all__ = ["create_app"]


def create_app(*, load_config: bool = True) -> FastAPI:
    """Create the FastAPI application.

    This is in a function rather than using a global variable (as is more
    typical for FastAPI) because we want to defer configuration loading until
    after the test suite has a chance to override the path to the
    configuration file.

    Parameters
    ----------
    load_config
        If set to `False`, do not try to load the configuration and skip any
        setup that requires the configuration. This is used primarily for
        OpenAPI schema generation, where constructing the app is required but
        the configuration won't matter.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await context_dependency.initialize()

        yield

        await context_dependency.aclose()
        await http_client_dependency.aclose()

    # Configure logging.
    if load_config:
        config = config_dependency.config
        configure_logging(
            name="ghostwriter",
            profile=config.profile,
            log_level=config.log_level,
        )
        configure_uvicorn_logging(config.log_level)

    logger = structlog.get_logger("ghostwriter")
    logger.debug("Created logger")

    # Create the application object.
    path_prefix = config.path_prefix if load_config else "/ghostwriter"
    app = FastAPI(
        title=config.name if load_config else "Ghostwriter",
        description=metadata("ghostwriter")["Summary"],
        version=version("ghostwriter"),
        openapi_url=f"{path_prefix}/openapi.json",
        docs_url=f"{path_prefix}/docs",
        redoc_url=f"{path_prefix}/redoc",
        lifespan=lifespan,
    )

    logger.debug("Created FastAPI app")

    # Attach the main controller routers.
    app.include_router(internal_router)
    app.include_router(external_router, prefix=f"{config.path_prefix}")

    logger.debug("Attached app routers")

    # Register middleware.
    app.add_middleware(XForwardedMiddleware)

    logger.debug("Registered middleware")

    # Configure Slack alerts.
    if load_config and config.alert_hook:
        webhook = str(config.alert_hook)
        SlackRouteErrorHandler.initialize(webhook, config.name, logger)
        logger.debug("Initialized Slack alert webhook")

    # Configure exception handlers.
    app.exception_handler(ClientRequestError)(client_request_error_handler)
    logger.debug("Configured exception handlers")

    return app


def create_openapi() -> str:
    """Generate the OpenAPI schema.

    Returns
    -------
    str
        OpenAPI schema as serialized JSON.
    """
    app = create_app(load_config=False)
    description = (
        app.description + "\n\n[Return to Ghostwriter documentation](.)"
    )
    schema = get_openapi(
        title=app.title,
        description=description,
        version=app.version,
        routes=app.routes,
    )
    return json.dumps(schema)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Set up and tear down the application."""
    # Any code here will be run when the application starts up.

    yield

    # Any code here will be run when the application shuts down.
    await http_client_dependency.aclose()
