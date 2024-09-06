"""Cache configured per-token RSP clients."""

import asyncio
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

        async def close_client(token: str, client: NubladoClient) -> None:
            try:
                await client.close()
            finally:
                del self._client_cache[token]

        await asyncio.gather(
            *(
                close_client(token, client)
                for token, client in self._client_cache.items()
            )
        )
