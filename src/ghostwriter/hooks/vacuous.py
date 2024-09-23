"""Does nothing, but if it loads, the hook machinery is working."""

import structlog

from ..models.substitution import Parameters


async def vacuous_hook(params: Parameters) -> None:
    """Load and execute a no-op."""
    logger = structlog.get_logger("ghostwriter")
    logger.debug(f"Vacuous hook called with {params}")
