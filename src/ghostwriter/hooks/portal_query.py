"""Takes a portal query ID from the request path and calls the Lab endpoint
to template and write that query.  We assume there's already a running lab,
which we can he sure of by putting ensure_running_lab in before this in the
hooks.
"""

from urllib.parse import urljoin

import structlog

from ..exceptions import HookError
from ..models.substitution import Parameters


async def portal_query(params: Parameters) -> None:
    """Create a portal query from a query ID."""
    logger = structlog.get_logger("ghostwriter")
    q_id = params.path.split("/")[-1]
    client = params.client
    http_client = client.http
    q_url = str(urljoin(params.base_url, f"/api/tap/async/{q_id}"))
    logger.debug(f"Portal query URL is {q_url}")
    body = {"type": "portal", "value": q_url}
    logger.debug(f"Logging in to hub as {params.user}")
    await client.auth_to_hub()
    logger.debug("Authenticating to lab")
    await client.auth_to_lab()
    logger.debug("Checking whether query notebook already exists")
    u_ep = str(urljoin(params.base_url, f"/nb/user/{params.user}"))
    nb_ep = f"{u_ep}/api/contents/notebooks/queries/portal_{q_id}.ipynb"
    resp = await http_client.get(nb_ep)
    if resp.status_code == 200:
        logger.debug(f"Notebook for query {q_id} exists.")
    else:
        endpoint = f"{u_ep}/rubin/query"
        logger.debug(f"Sending POST to {endpoint}")
        xsrf = client.lab_xsrf
        headers = {"Content-Type": "application/json"}
        if xsrf:
            headers["X-XSRFToken"] = xsrf
        resp = await http_client.post(endpoint, json=body, headers=headers)
        if resp.status_code >= 400:
            raise HookError(f"POST to {endpoint} failed: {resp}")
        logger.debug("Continuing to redirect")
