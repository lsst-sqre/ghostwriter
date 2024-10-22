"""Does nothing, but if it loads, the hook machinery is working."""

from ..models.substitution import Parameters
from ._logger import LOGGER


async def vacuous_hook(params: Parameters) -> None:
    """Load and execute a no-op."""
    LOGGER.debug(f"Vacuous hook called with {params}")
