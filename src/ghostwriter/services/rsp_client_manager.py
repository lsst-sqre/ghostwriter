"""Cache configured per-token RSP clients."""

import datetime

from pydantic import HttpUrl
from rsp_jupyter_client import RSPJupyterClient
from structlog.stdlib import BoundLogger

from ..constants import HTTP_TIMEOUT
from ..storage.gafaelfawr import GafaelfawrManager


class RSPClientManager:
    """Maintain a cache of tokens to RSP HTTP clients."""

    def __init__(
        self,
        base_url: HttpUrl,
        gafaelfawr_manager: GafaelfawrManager,
        logger: BoundLogger,
    ) -> None:
        self._base_url = base_url
        self._gafaelfawr_manager = gafaelfawr_manager
        self._logger = logger
        self._client_cache: dict[str, RSPJupyterClient] = {}
        self._logger.debug("Initialized RSPClientManager")

    async def get_client(self, token: str) -> RSPJupyterClient:
        """Get a configured RSP client from a token."""
        if token not in self._client_cache:
            user = await self._gafaelfawr_manager.get_user(token)
            self._client_cache[token] = RSPJupyterClient(
                timeout=datetime.timedelta(seconds=HTTP_TIMEOUT),
                logger=self._logger,
                user=user,
                base_url=str(self._base_url),
            )
            self._logger.debug(
                f"Built RSPJupyterClient for user {user.username}"
            )
        return self._client_cache[token]

    async def aclose(self) -> None:
        """Shut down all our clients."""
        for token in list(self._client_cache.keys()):
            await self._client_cache[token].close()
            del self._client_cache[token]
