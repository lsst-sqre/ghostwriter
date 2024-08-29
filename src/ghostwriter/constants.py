"""Constants for ghostwriter."""

from pathlib import Path

__all__ = ["CONFIGURATION_PATH", "HTTP_TIMEOUT", "ROUTING_PATH"]

CONFIGURATION_PATH = Path("/etc/ghostwriter/config.yaml")
"""Default path to controller configuration."""

HTTP_TIMEOUT = 20.0
"""Default timeout (in seconds) for outbound HTTP requests.

The default HTTPX timeout has proven too short in practice for calls to, for
example, GitHub for authorization verification. Increase the default to 20
seconds. Users of this dependency can always lower it if needed.
"""

ROUTING_PATH = Path("/etc/ghostwriter/routing.yaml")
"""Default path to route-substitution configuration."""
