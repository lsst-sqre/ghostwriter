"""Substitution parameters for a route transformation."""

from dataclasses import dataclass


@dataclass
class Parameters:
    """Parameters needed for route transformation."""

    user: str
    base_url: str
    path: str
    token: str

    def to_dict(self) -> dict[str, str]:
        """Produce dictionary representation of parameters."""
        return {
            "user": self.user,
            "base_url": self.base_url,
            "path": self.path,
            "token": self.token,
        }
