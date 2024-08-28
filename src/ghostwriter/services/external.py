"""Handlers for the app's external root, ``/ghostwriter/``."""

from typing import Annotated
from urllib.parse import urljoin

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from safir.dependencies.logger import logger_dependency
from safir.metadata import get_metadata
from structlog.stdlib import BoundLogger

from ..config import config
from ..dependencies.context import RequestContext, context_dependency
from ..models.index import Index

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
    "/ghostwriter/rewrite/{full_path:path}",
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
    user = context.user
    base_url = str(context.factory.context.base_url)
    (key, path) = full_path.split(
        sep="/", maxsplit=1
    )  # ValueError if no split
    mapping = context.factory.context.mapping
    if key not in mapping:
        raise ValueError(f"No mapping for '{key}'")
    resolved = mapping.key.format(user=user)
    url = urljoin(base_url, resolved)
    return RedirectResponse(str(url))
