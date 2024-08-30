"""Handlers for the app's external root, ``/ghostwriter/``."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from safir.dependencies.logger import logger_dependency
from safir.metadata import get_metadata
from structlog.stdlib import BoundLogger

from ..config import Configuration
from ..dependencies.config import config_dependency
from ..dependencies.context import RequestContext, context_dependency
from ..models.index import Index
from ..models.substitution import Parameters

__all__ = ["get_index", "external_router"]

external_router = APIRouter()
"""FastAPI router for all external handlers."""


@external_router.get(
    "/",
    description=(
        "Document the top-level API here. By default it only returns metadata"
        " about the application."
    ),
    response_model=Index,
    response_model_exclude_none=True,
    summary="Application metadata",
)
async def get_index(
    logger: Annotated[BoundLogger, Depends(logger_dependency)],
    config: Annotated[Configuration, Depends(config_dependency)],
) -> Index:
    """GET ``/ghostwriter/`` (the app's external root).

    Customize this handler to return whatever the top-level resource of your
    application should return. For example, consider listing key API URLs.
    When doing so, also change or customize the response model in
    `ghostwriter.models.index.Index`.

    By convention, the root of the external API includes a field called
    ``metadata`` that provides the same Safir-generated metadata as the
    internal root endpoint.
    """
    # There is no need to log simple requests since uvicorn will do this
    # automatically, but this is included as an example of how to use the
    # logger for more complex logging.
    logger.info("Request for application metadata")

    metadata = get_metadata(
        package_name="ghostwriter",
        application_name=config.name,
    )
    return Index(metadata=metadata)


@external_router.api_route(
    "/rewrite/{full_path:path}",
    methods=[
        "GET",
        "PUT",
        "POST",
        "DELETE",
        "PATCH",
        "HEAD",
        "CONNECT",
        "OPTIONS",
        "TRACE",
    ],
)
async def rewrite(
    full_path: str,
    context: Annotated[RequestContext, Depends(context_dependency)],
) -> RedirectResponse:
    params = Parameters(
        user=context.user,
        token=context.token,
        base_url=str(context.factory.context.base_url),
        path=full_path,
    )
    mapping = context.factory.context.mapping
    resolved = await mapping.resolve(params)
    return RedirectResponse(resolved)
