"""Cache configured per-token RSP clients."""

import datetime

from pydantic import HttpUrl
from rubin.nublado.client import NubladoClient
from structlog.stdlib import BoundLogger

from ..constants import HTTP_TIMEOUT
from ..storage.gafaelfawr import GafaelfawrManager


class ClientManager:
    """Maintain a cache of tokens to Nublado HTTP clients."""

    def __init__(
        self,
        base_url: HttpUrl,
        gafaelfawr_manager: GafaelfawrManager,
        logger: BoundLogger,
    ) -> None:
        self._base_url = base_url
        self._gafaelfawr_manager = gafaelfawr_manager
        self._logger = logger
        self._client_cache: dict[str, NubladoClient] = {}
        self._logger.debug("Initialized ClientManager")

    async def get_client(self, token: str) -> NubladoClient:
        """Get a configured Nublado client from a token."""
        if token not in self._client_cache:
            user = await self._gafaelfawr_manager.get_user(token)
            self._client_cache[token] = NubladoClient(
                timeout=datetime.timedelta(seconds=HTTP_TIMEOUT),
                logger=self._logger,
                user=user,
                base_url=str(self._base_url),
            )
            self._logger.debug(f"Built NubladoClient for user {user.username}")
        return self._client_cache[token]

    async def aclose(self) -> None:
        """Shut down all our clients."""
        for token in list(self._client_cache.keys()):
            await self._client_cache[token].close()
            del self._client_cache[token]
