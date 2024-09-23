"""Constants for ghostwriter."""

from pathlib import Path

__all__ = ["CONFIGURATION_PATH", "HTTP_TIMEOUT", "ROUTING_PATH"]

CONFIGURATION_PATH = Path("/etc/ghostwriter/config.yaml")
"""Default path to controller configuration."""

HTTP_TIMEOUT = 30.0
"""Default timeout (in seconds) for outbound HTTP requests.

The default HTTPX timeout has proven too short in practice for calls to, for
example, JupyterHub to request Python code execution.
"""

ROUTING_PATH = Path("/etc/ghostwriter/routing.yaml")
"""Default path to route-substitution configuration."""
