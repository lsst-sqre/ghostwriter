"""Substitution parameters for a route transformation."""

from dataclasses import dataclass

from rubin.nublado.client import NubladoClient


@dataclass
class Parameters:
    """Parameters and clients needed for route transformation and hook
    execution.  Note that target and unique_id should be intially unset,
    although they may be updated during hook processing.
    """

    user: str
    base_url: str
    path: str
    token: str
    client: NubladoClient
    target: str | None = None
    unique_id: str | None = None

    def __str__(self) -> str:
        ret = f"Parameters[User: '{self.user}'; Base URL '{self.base_url}'; "
        ret += f"Path: '{self.path}'; "
        if self.target:
            ret += f"Target: '{self.target}'; "
        if self.unique_id:
            ret += f"UniqueID: {self.unique_id}; "
        ret += "Token and RSP client redacted]"
        return ret

    def rewrite_mapping(self) -> dict[str, str]:
        """Return sanitized version for rewriting path."""
        # source_prefix will begin with a slash, so base_url should have its
        # stripped.
        base_url = self.base_url.rstrip("/")
        return {
            "user": self.user,
            "base_url": base_url,
            "path": self.path,
            "target": self.target or "",
            "unique_id": self.unique_id or "",
        }
