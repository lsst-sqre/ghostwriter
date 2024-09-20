"""Cache configured per-token RSP clients."""

import asyncio
import datetime

from pydantic import HttpUrl
from rubin.nublado.client import NubladoClient
from rubin.nublado.client.models import User
from structlog.stdlib import BoundLogger

from ..constants import HTTP_TIMEOUT


class ClientManager:
    """Maintain a cache of tokens to Nublado HTTP clients."""

    def __init__(
        self,
        base_url: HttpUrl,
        logger: BoundLogger,
    ) -> None:
        self._base_url = base_url
        self._logger = logger
        self._client_cache: dict[str, NubladoClient] = {}
        self._logger.debug("Initialized ClientManager")

    async def get_client(self, username: str, token: str) -> NubladoClient:
        """Get a configured Nublado client from a user and token."""
        if token not in self._client_cache:
            self._client_cache[token] = NubladoClient(
                logger=self._logger,
                user=User(username=username, token=token),
                base_url=str(self._base_url),
                timeout=datetime.timedelta(seconds=HTTP_TIMEOUT),
            )
            self._logger.debug(f"Built NubladoClient for user {username}")
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
