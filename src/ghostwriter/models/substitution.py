"""Substitution parameters for a route transformation."""

from dataclasses import dataclass


@dataclass
class Parameters:
    """Parameters needed for route transformation."""

    user: str
    base_url: str
    path: str
    token: str

    def __str__(self) -> str:
        return (
            f"Parameters[User: '{self.user}'; Base URL '{self.base_url}'"
            f" Path: '{self.path}'; Token <redacted>."
        )
