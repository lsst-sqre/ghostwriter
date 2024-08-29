"""Constants for ghostwriter."""

from pathlib import Path

__all__ = ["CONFIGURATION_PATH"]

CONFIGURATION_PATH = Path("/etc/ghostwriter/config.yaml")
"""Default path to controller configuration."""

ROUTING_PATH = Path("/etc/ghostwriter/routing.yaml")
"""Default path to route-substitution configuration."""
