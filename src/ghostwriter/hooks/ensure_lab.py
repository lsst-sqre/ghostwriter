"""Ensure that the user has a running lab by dropping them in the spawner form
if they don't, and then slingshotting them through the lab ghostwriter endpoint
to restart the redirect process.  Requires d_2024_10_19 (corresponds to
w_2024_10_43) or later.
"""

from ..models.substitution import Parameters
from ._logger import LOGGER


async def ensure_running_lab(params: Parameters) -> Parameters | None:
    """Start a Lab if one is not present."""
    LOGGER.debug(f"Checking for running Lab for {params}")
    client = params.client
    LOGGER.debug("Logging in to Hub")
    await client.auth_to_hub()
    stopped = await client.is_lab_stopped()
    if not stopped:
        LOGGER.debug(f"{params.user} already has a running Lab")
        return None
    LOGGER.debug(f"Sending {params.user} to spawner")
    LOGGER.debug(f"Input parameters {params}")
    new_p = Parameters(
        user=params.user,
        base_url=params.base_url,
        path=params.path,
        token=params.token,
        client=params.client,
        target="${base_url}/nb/user/${user}/rubin/ghostwriter/${path}",
        unique_id=params.unique_id,
        strip=False,
        final=True,
    )
    LOGGER.debug(f"Output parameters {new_p}")
    return new_p
