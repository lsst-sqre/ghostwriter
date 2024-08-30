"""Request context dependency for FastAPI.

This dependency gathers a variety of information into a single object for the
convenience of writing request handlers.  It also provides a place to store a
`structlog.BoundLogger` that can gather additional context during processing,
including from dependencies, and provides a token-specific HTTP client for the
RSP, which in addition to functioning as a normal HTTP client is able to
execute Python inside the context of a user notebook session, which is needed
for some hooks.
"""

import datetime
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Request
from rsp_jupyter_client import RSPJupyterClient
from safir.dependencies.gafaelfawr import (
    auth_delegated_token_dependency,
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

    rsp_client: RSPJupyterClient
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
        self._client_cache: dict[str, RSPJupyterClient] = {}

    async def __call__(
        self,
        request: Request,
        logger: Annotated[BoundLogger, Depends(auth_logger_dependency)],
        token: Annotated[str, Depends(auth_delegated_token_dependency)],
    ) -> RequestContext:
        """Create a per-request context."""
        logger.debug("Creating request context.")
        pc = self.process_context
        if token not in self._client_cache:
            logger.debug("Creating new RSPJupyterClient")
            user = await pc.gafaelfawr_manager.get_user(token)
            logger.debug(f"Resolved user {user.username} from token")
            self._client_cache[token] = RSPJupyterClient(
                logger=logger,
                timeout=datetime.timedelta(seconds=HTTP_TIMEOUT),
                user=user,
                base_url=str(pc.base_url),
            )
            logger.debug(f"Built RSPJupyterClient for user {user.username}")
        rsp_client = self._client_cache[token]

        rc = RequestContext(
            request=request,
            logger=logger,
            user=user.username,
            token=token,
            rsp_client=rsp_client,
            factory=Factory(pc, logger),
        )

        logger.debug(
            f"Created request context for {request} by {user.username}"
        )
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
        # Remove all our cached HTTP clients
        del_cli: list[str] = []  # Don't modify dict while looping over it.
        for tok in self._client_cache:
            await self._client_cache[tok].close()
            del_cli.append(tok)
        for tok in del_cli:
            del self._client_cache[tok]
        if self._process_context:
            await self._process_context.aclose()
        self._process_context = None


context_dependency = ContextDependency()
"""The dependency that will return the per-request context."""
