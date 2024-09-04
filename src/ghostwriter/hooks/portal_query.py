"""Takes a portal query ID from the request path and calls the Lab endpoint
to template and write that query.  We assume there's already a running lab,
which we can he sure of by putting ensure_running_lab in before this in the
hooks.
"""

from urllib.parse import urljoin

import structlog

from ..models.substitution import Parameters


async def portal_query(params: Parameters) -> None:
    """Create a portal query from a query ID."""
    logger = structlog.get_logger("ghostwriter")
    q_id = params.path.split("/")[-1]
    rsp_client = params.client
    http_client = rsp_client.http
    q_url = str(urljoin(params.base_url, f"/api/tap/async/{q_id}"))
    logger.debug(f"Portal query URL is {q_url}")
    body = {"type": "portal", "value": q_url}
    logger.debug(f"Logging in to hub as {params.user}")
    await rsp_client.auth_to_hub()
    logger.debug("Authenticating to lab")
    await rsp_client.auth_to_lab()
    endpoint = str(
        urljoin(params.base_url, f"/nb/user/{params.user}/rubin/query")
    )
    logger.debug(f"Sending POST to {endpoint}")
    await http_client.post(endpoint, json=body)
    logger.debug("Continuing to redirect")
