"""Does nothing, but if it loads, the hook machinery is working."""

import structlog

from ..models.substitution import Parameters

LOGGER = structlog.get_logger("ghostwriter")


async def vacuous_hook(params: Parameters) -> None:
    """Load and execute a no-op."""
    LOGGER.debug(f"Vacuous hook called with {params}")
