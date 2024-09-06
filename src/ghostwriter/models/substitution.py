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

    def __str__(self) -> str:
        return (
            f"Parameters[User: '{self.user}'; Base URL '{self.base_url}'"
            f" Path: '{self.path}'; Token and RSP client <redacted>]"
        )

    def rewrite_mapping(self) -> dict[str, str]:
        """Return sanitized version for rewriting path."""
        return {
            "user": self.user,
            "base_url": self.base_url,
            "path": self.path,
        }
