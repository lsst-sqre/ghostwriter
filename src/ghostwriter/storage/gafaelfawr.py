"""Starting from a token (x-auth-delegated-token), construct an authenticated
Gafaelfawr user for use in the per-request http client, and maintain a cache
of those objects.
"""

from urllib.parse import urljoin

from pydantic import HttpUrl
from rubin.nublado.client.models.user import AuthenticatedUser
from safir.dependencies.http_client import http_client_dependency


class GafaelfawrManager:
    """Maintain a cache of tokens to AuthenticatedUsers for construction
    of RSP HTTP clients.
    """

    def __init__(self, base_url: HttpUrl) -> None:
        self._base_url = base_url
        self._user_cache: dict[str, AuthenticatedUser] = {}

    async def get_user(self, token: str) -> AuthenticatedUser:
        if token not in self._user_cache:
            # We need fields from two calls.
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            }
            api = urljoin(str(self._base_url), "/auth/api/v1")
            client = await http_client_dependency()
            token_info = (
                await client.get(f"{api}/token-info", headers=headers)
            ).json()
            user_info = (
                await client.get(
                    f"{api}/user-info",
                    headers=headers,
                )
            ).json()
            user = AuthenticatedUser(
                username=user_info["username"],
                uidnumber=user_info["uid"],
                gidnumber=user_info["gid"],
                scopes=token_info["scopes"],
                token=token,
            )
            self._user_cache[token] = user
        return self._user_cache[token]
