"""HTTP client dependency for FastAPI.  This differs from the Safir-provided
dependency in that it is itself dependent on having an auth token, and there
is a separate client per token.
"""

from __future__ import annotations

from typing import Annotated

import httpx
from pydantic import Depends
from safir.dependencies.gafaelfawr import auth_delegated_token_dependency

__all__ = [
    "DEFAULT_HTTP_TIMEOUT",
    "HTTPClientDependency",
    "http_client_dependency",
]

DEFAULT_HTTP_TIMEOUT = 20.0
"""Default timeout (in seconds) for outbound HTTP requests.

The default HTTPX timeout has proven too short in practice for calls to, for
example, GitHub for authorization verification. Increase the default to 20
seconds. Users of this dependency can always lower it if needed.
"""


class HTTPClientDependency:
    """Provides an ``httpx.AsyncClient`` as a dependency.

    The resulting client will have redirects enabled and the default timeout
    increased to 20 seconds.

    Notes
    -----
    The application must call ``http_client_dependency.aclose()`` in the
    application lifespan hook:

    .. code-block:: python

       from collections.abc import AsyncIterator
       from contextlib import asynccontextmanager

       from fastapi import FastAPI


       @asynccontextmanager
       async def lifespan(app: FastAPI) -> AsyncIterator[None]:
           yield
           await http_client_dependency.aclose()


       app = FastAPI(lifespan=lifespan)
    """

    def __init__(self) -> None:
        self._http_client: dict[str, httpx.AsyncClient] = {}

    async def __call__(
        self,
        token: Annotated[str, Depends(auth_delegated_token_dependency)],
    ) -> httpx.AsyncClient:
        """Return the cached ``httpx.AsyncClient`` for the token."""
        if token not in self._http_client:
            self._http_client[token] = httpx.AsyncClient(
                timeout=DEFAULT_HTTP_TIMEOUT, follow_redirects=True
            )
        return self._http_client[token]

    async def aclose(self) -> None:
        """Close all ``httpx.AsyncClient``s."""
        for token in self._http_client:
            await self._http_client[token].aclose()
            del self._http_client[token]


http_client_dependency = HTTPClientDependency()
"""The dependency that will return the HTTP client."""
