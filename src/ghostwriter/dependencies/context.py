"""Request context dependency for FastAPI.

This dependency gathers a variety of information into a single object for the
convenience of writing request handlers.  It also provides a place to store a
`structlog.BoundLogger` that can gather additional context during processing,
including from dependencies.
"""

from dataclasses import dataclass
from typing import Annotated, Any

import httpx
from fastapi import Depends, Request
from safir.dependencies.gafaelfawr import (
    auth_delegated_token_dependency,
    auth_dependency,
    auth_logger_dependency,
)
from structlog.stdlib import BoundLogger

from ..constants import HTTP_TIMEOUT
from ..factory import Factory, ProcessContext

__all__ = [
    "ContextDependency",
    "RequestContext",
    "context_dependency",
]


@dataclass(slots=True)
class RequestContext:
    """Holds the incoming request and its surrounding context."""

    request: Request
    """Incoming request."""

    logger: BoundLogger
    """Request logger, rebound with discovered context."""

    factory: Factory
    """Component factory."""

    user: str
    """Authenticated user."""

    token: str
    """Token corresponding to authenticated user."""

    http_client: httpx.AsyncClient
    """HTTP Client initialized with correct token."""

    def rebind_logger(self, **values: Any) -> None:
        """Add the given values to the logging context.

        Parameters
        ----------
        **values
            Additional values that should be added to the logging context.
        """
        self.logger = self.logger.bind(**values)
        self.factory.set_logger(self.logger)


class ContextDependency:
    """Provide a per-request context as a FastAPI dependency.

    Each request gets a `RequestContext`.  To save overhead, the portions of
    the context that are shared by all requests are collected into the single
    process-global `~ghostwriter.factory.ProcessContext` and reused with each
    request.
    """

    def __init__(self) -> None:
        self._process_context: ProcessContext | None = None
        self._client_cache: dict[str, httpx.AsyncClient] = {}

    async def __call__(
        self,
        request: Request,
        logger: Annotated[BoundLogger, Depends(auth_logger_dependency)],
        user: Annotated[str, Depends(auth_dependency)],
        token: Annotated[str, Depends(auth_delegated_token_dependency)],
    ) -> RequestContext:
        """Create a per-request context."""
        if not self._process_context:
            raise RuntimeError("ContextDependency not initialized")
        if token not in self._client_cache:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            self._client_cache[token] = httpx.AsyncClient(
                timeout=HTTP_TIMEOUT,
                follow_redirects=True,
                headers=headers,
                base_url=str(self._process_context.base_url),
            )
        http_client = self._client_cache[token]

        return RequestContext(
            request=request,
            logger=logger,
            user=user,
            token=token,
            http_client=http_client,
            factory=Factory(self._process_context, logger),
        )

    @property
    def process_context(self) -> ProcessContext:
        if not self._process_context:
            raise RuntimeError("ContextDependency not initialized")
        return self._process_context

    async def initialize(self) -> None:
        """Initialize the process-wide shared context."""
        if self._process_context:
            await self._process_context.aclose()
        self._process_context = ProcessContext()

    async def aclose(self) -> None:
        """Clean up the per-process configuration."""
        # Remove all our cached HTTP clients
        del_cli: list[str] = []  # Don't modify dict while looping over it.
        for tok in self._client_cache:
            await self._client_cache[tok].aclose()
            del_cli.append(tok)
        for tok in del_cli:
            del self._client_cache[tok]
        if self._process_context:
            await self._process_context.aclose()
        self._process_context = None


context_dependency = ContextDependency()
"""The dependency that will return the per-request context."""
