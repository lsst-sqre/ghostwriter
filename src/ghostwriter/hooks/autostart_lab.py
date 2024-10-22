"""Ensure that the user has a running lab.  If they don't, they will be
given `recommended` in `medium` size.
"""

import asyncio

from rubin.nublado.client import NubladoClient
from rubin.nublado.client.models import (
    NubladoImage,
    NubladoImageByClass,
    NubladoImageClass,
    NubladoImageSize,
)

from ..models.substitution import Parameters
from ._logger import LOGGER

LAB_SPAWN_TIMEOUT = 90


async def ensure_autostart_lab(params: Parameters) -> None:
    """Start a Lab if one is not present."""
    LOGGER.debug(f"Checking for running Lab for {params}")
    client = params.client
    LOGGER.debug("Logging in to Hub")
    await client.auth_to_hub()
    stopped = await client.is_lab_stopped()
    if stopped:
        LOGGER.debug(f"Starting new 'recommended' Lab for {params.user}")
        await _spawn_lab(client)
    else:
        LOGGER.debug(f"{params.user} already has a running Lab")
    LOGGER.debug("Lab spawned; proceeding with redirection")


async def _spawn_lab(client: NubladoClient) -> None:
    image = _choose_image()
    await client.spawn_lab(image)
    await _follow_progress(client)


def _choose_image() -> NubladoImage:
    """Because the primary use case of this redirection service is
    to launch tutorial notebooks, our "start a new lab" parameters
    are going to be the currently recommended lab, and Medium size,
    because that's how the tutorial notebooks are generally set up
    to run.  Maybe we will do something more sophisticated later.
    """
    return NubladoImageByClass(
        image_class=NubladoImageClass.RECOMMENDED, size=NubladoImageSize.Medium
    )


async def _follow_progress(client: NubladoClient) -> None:
    LOGGER.debug("Waiting for lab to spawn")
    progress = client.watch_spawn_progress()
    try:
        async with asyncio.timeout(LAB_SPAWN_TIMEOUT):
            async for message in progress:
                LOGGER.debug(f"Lab spawn message: {message.message}")
                if message.ready:
                    break
    except TimeoutError:
        LOGGER.exception(f"Lab did not spawn in {LAB_SPAWN_TIMEOUT} seconds")
        raise
