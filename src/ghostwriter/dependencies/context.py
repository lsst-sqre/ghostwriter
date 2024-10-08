"""Request context dependency for FastAPI.

This dependency gathers a variety of information into a single object for the
convenience of writing request handlers.  It also provides a place to store a
`structlog.BoundLogger` that can gather additional context during processing,
including from dependencies, and provides a token-specific HTTP client for the
RSP, which in addition to functioning as a normal HTTP client is able to
execute Python inside the context of a user notebook session, which is needed
for some hooks.
"""

from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Request
from rubin.nublado.client import NubladoClient
from safir.dependencies.gafaelfawr import (
    auth_delegated_token_dependency,
    auth_dependency,
    auth_logger_dependency,
)
from structlog.stdlib import BoundLogger

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

    client: NubladoClient
    """RSP Client initialized with correct token."""

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

    async def __call__(
        self,
        request: Request,
        username: Annotated[str, Depends(auth_dependency)],
        logger: Annotated[BoundLogger, Depends(auth_logger_dependency)],
        token: Annotated[str, Depends(auth_delegated_token_dependency)],
    ) -> RequestContext:
        """Create a per-request context."""
        logger.debug("Creating request context.")
        pc = self.process_context
        client = await pc.client_manager.get_client(username, token)

        rc = RequestContext(
            request=request,
            logger=logger,
            user=username,
            token=token,
            client=client,
            factory=Factory(pc, logger),
        )

        logger.debug(f"Created request context for {request} by {username}")
        return rc

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
        if self._process_context:
            await self._process_context.aclose()
        self._process_context = None


context_dependency = ContextDependency()
"""The dependency that will return the per-request context."""
