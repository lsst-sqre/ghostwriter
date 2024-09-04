"""Ensure that the user has a running lab."""

import asyncio

import structlog
from rsp_jupyter_client.models.image import (
    NubladoImageByClass,
    NubladoImageClass,
    NubladoImageSize,
)

from ..models.substitution import Parameters

SPAWN_TIMEOUT = 90


async def ensure_running_lab(params: Parameters) -> None:
    """Start a Lab if one is not present."""
    logger = structlog.get_logger("ghostwriter")
    logger.debug(f"Checking for running Lab for {params}")
    client = params.client
    logger.debug("Logging in to Hub")
    await client.auth_to_hub()
    stopped = await client.is_lab_stopped()
    if stopped:
        logger.debug(f"Starting new 'recommended' lab for {params.user}")
        #
        # Because the primary use case of this redirection service is
        # to launch tutorial notebooks, our "start a new lab" parameters
        # are going to be the currently recommended lab, and Medium size,
        # because that's how the tutorial notebooks are generally set up
        # to run.
        #
        image = NubladoImageByClass(
            image_class=NubladoImageClass.RECOMMENDED,
            size=NubladoImageSize.Medium,
        )
        await client.spawn_lab(image)
        logger.debug("Waiting for lab to spawn")
        progress = client.watch_spawn_progress()
        try:
            async with asyncio.timeout(SPAWN_TIMEOUT):
                async for message in progress:
                    logger.debug(f"Lab spawn message: {message.message}")
                    if message.ready:
                        break
        except TimeoutError:
            logger.exception(f"Lab did not spawn in {SPAWN_TIMEOUT} seconds")
            raise
        logger.debug("Lab spawned; proceeding with redirection")
