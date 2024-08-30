"""Substitution parameters for a route transformation."""

from dataclasses import dataclass


@dataclass
class Parameters:
    """Parameters needed for route transformation."""

    user: str
    base_url: str
    path: str
    token: str
