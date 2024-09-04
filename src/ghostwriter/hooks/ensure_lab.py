"""Ensure that the user has a running lab."""

import structlog

from ..models.substitution import Parameters

LOGGER = structlog.get_logger("ghostwriter")


async def ensure_running_lab(params: Parameters) -> None:
    """Start a Lab if one is not present."""
