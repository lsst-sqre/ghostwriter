"""Substitution parameters for a route transformation."""

from dataclasses import dataclass

from rubin.nublado.client import NubladoClient


@dataclass
class Parameters:
    """Parameters and clients needed for route transformation and hook
    execution.
    """

    user: str
    base_url: str
    path: str
    token: str
    client: NubladoClient
    unique_id: str | None = None

    def __str__(self) -> str:
        ret = f"Parameters[User: '{self.user}'; Base URL '{self.base_url}'"
        ret += f" Path: '{self.path}; "
        if self.unique_id:
            ret += f"UniqueID: {self.unique_id}; "
        ret += "Token and RSP client redacted]"
        return ret

    def rewrite_mapping(self) -> dict[str, str]:
        """Return sanitized version for rewriting path."""
        return {
            "user": self.user,
            "base_url": self.base_url,
            "path": self.path,
            "unique_id": self.unique_id or "",
        }
