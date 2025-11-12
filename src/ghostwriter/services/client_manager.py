"""Cache configured per-token RSP clients."""

import datetime

from rubin.nublado.client import NubladoClient
from structlog.stdlib import BoundLogger

from ..constants import HTTP_TIMEOUT


class ClientManager:
    """Maintain a cache of tokens to Nublado HTTP clients."""

    def __init__(self, logger: BoundLogger) -> None:
        self._logger = logger
        self._client_cache: dict[str, NubladoClient] = {}
        self._logger.debug("Initialized ClientManager")

    async def get_client(self, username: str, token: str) -> NubladoClient:
        """Get a configured Nublado client from a user and token."""
        if token not in self._client_cache:
            self._client_cache[token] = NubladoClient(
                username,
                token,
                logger=self._logger,
                timeout=datetime.timedelta(seconds=HTTP_TIMEOUT),
            )
            self._logger.debug(f"Built NubladoClient for user {username}")
        return self._client_cache[token]

    async def aclose(self) -> None:
        """Shut down all our clients."""
        cache = self._client_cache
        self._client_cache = {}
        for client in cache.values():
            await client.aclose()
