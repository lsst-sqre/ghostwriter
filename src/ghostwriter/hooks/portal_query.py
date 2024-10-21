"""Takes a portal query ID from the request path and calls the Lab endpoint
to template and write that query.  We assume there's already a running lab,
which we can he sure of by putting ensure_running_lab in before this in the
hooks.
"""

from urllib.parse import urljoin

from rubin.nublado.client import NubladoClient

from ..exceptions import HookError
from ..models.substitution import Parameters
from ._logger import LOGGER


async def portal_query(params: Parameters) -> None:
    """Create a portal query from a query ID."""
    client = params.client
    query_id = _get_query_id(params.path)
    query_url = _get_tap_url(base_url=params.base_url, query_id=query_id)
    user_ep = _get_user_endpoint(params.base_url, params.user)
    LOGGER.debug("TAP query URL", query_url=query_url)
    LOGGER.debug("Logging in to hub", user=params.user)
    await client.auth_to_hub()
    LOGGER.debug("Authenticating to lab")
    await client.auth_to_lab()
    LOGGER.debug("Checking whether query notebook already exists")
    nb_exists = await _check_query_notebook(
        client=client,
        query_id=query_id,
        query_url=query_url,
        user_endpoint=user_ep,
    )
    if not nb_exists:
        LOGGER.debug("Creating query notebook", query_id=query_id)
        await _create_query_notebook(
            client=client,
            query_url=query_url,
            user_endpoint=user_ep,
        )
    LOGGER.debug("Continuing to redirect")


def _get_query_id(path: str) -> str:
    # The input path is .../queries/<query-id>, so it's just the last
    # component.  The only way the path wouldn't have at least one slash in
    # it is if someone has really horrifically messed up their routing
    # definition.
    return path.split("/")[-1]


def _get_tap_url(base_url: str, query_id: str) -> str:
    # Construct the tap query endpoint from our base_url and convention
    async_query_url = "/api/tap/async"
    return str(urljoin(base_url, f"{async_query_url}/{query_id}"))


def _get_user_endpoint(base_url: str, user: str) -> str:
    return str(urljoin(base_url, f"/nb/user/{user}"))


async def _check_query_notebook(
    client: NubladoClient,
    query_id: str,
    query_url: str,
    user_endpoint: str,
) -> bool:
    nb_endpoint = (
        f"{user_endpoint}/files/notebooks/queries/portal_{query_id}.ipynb"
    )
    resp = await client.http.head(nb_endpoint)
    if resp.status_code == 200:
        LOGGER.debug("Notebook for query exists", query_id=query_id)
        return True
    return False


async def _create_query_notebook(
    client: NubladoClient,
    query_url: str,
    user_endpoint: str,
) -> None:
    body = {"type": "portal", "value": query_url}
    query_endpoint = f"{user_endpoint}/rubin/query"
    xsrf = client.lab_xsrf
    headers = {"Content-Type": "application/json"}
    if xsrf:
        headers["X-XSRFToken"] = xsrf
    LOGGER.debug(f"Sending POST to {query_endpoint}")
    resp = await client.http.post(query_endpoint, json=body, headers=headers)
    if resp.status_code >= 400:
        raise HookError(f"POST to {query_endpoint} failed: {resp}")
