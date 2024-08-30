"""Starting from a token (x-auth-delegated-token), construct an authenticated
Gafaelfawr user for use in the per-request http client, and maintain a cache
of those objects.
"""

from httpx import AsyncClient
from pydantic import HttpUrl
from rsp_jupyter_client.models.user import AuthenticatedUser


class GafaelfawrManager:
    """Maintain a cache of tokens to AuthenticatedUsers for construction
    of RSP HTTP clients.
    """

    def __init__(self, base_url: HttpUrl) -> None:
        self._user_cache: dict[str, AuthenticatedUser] = {}
        self._client = AsyncClient(
            base_url=str(base_url),
            headers={"Content-Type": "application/json"},
            follow_redirects=True,
        )

    async def get_user(self, token: str) -> AuthenticatedUser:
        if token in self._user_cache:
            return self._user_cache[token]
        # We need fields from two calls.
        self._client.headers["Authorization"] = f"Bearer {token}"
        api = "/auth/api/v1"
        token_info = (await self._client.get(f"{api}/token-info")).json()
        user_info = (await self._client.get(f"{api}/user-info")).json()
        del self._client.headers["Authorization"]
        user = AuthenticatedUser(
            username=user_info["username"],
            uidnumber=user_info["uid"],
            gidnumber=user_info["gid"],
            scopes=token_info["scopes"],
            token=token,
        )
        self._user_cache[token] = user
        return user
