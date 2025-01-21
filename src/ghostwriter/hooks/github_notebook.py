"""Takes a GitHub notebook repo/owner/path from the request path and
puts it into the user's lab environment.  We assume there's already a running
lab, which we can be sure of by putting ensure_running_lab in before this in
the hooks.
"""

import inspect
from pathlib import Path
from string import Template
from urllib.parse import urljoin

from ..models.substitution import Parameters
from ._logger import LOGGER


async def github_notebook(params: Parameters) -> Parameters:
    """Check out a particular notebook from GitHub."""
    client = params.client
    LOGGER.debug("Logging in to hub", user=params.user)
    await client.auth_to_hub()
    LOGGER.debug("Authenticating to lab")
    await client.auth_to_lab()
    async with client.open_lab_session() as lab_session:
        code = _get_code_from_template(params.path)
        LOGGER.debug("Code for execution in Lab context", code=code)
        # We know the stream output should be the serial number and
        # a newline.
        serial = (await lab_session.run_python(code)).strip()

    # Honestly it's easier to just unconditionally rewrite the target
    # than to figure out whether it needs rewriting.

    return _get_new_params(serial, params)


def _get_new_params(serial: str, params: Parameters) -> Parameters:
    # Start with the common fragment
    target = (
        f"{params.base_url}nb/user/{params.user}/lab/tree/notebooks"
        "/on-demand/github.com/"
    )

    # Remove branch information, if any (the checkout will have handled
    # it in the code we ran to get the serial).
    path = params.path.split("@")[0]

    # Canonicalize path.
    prefix = "notebooks/github.com/"
    path = path.removeprefix(prefix)
    if path.endswith(".ipynb"):
        # Also needs stripping
        path = path[: -(len(".ipynb"))]

    # Add discriminator if needed
    unique_id: str | None = None
    if serial and serial != "0":
        # Glue in serial if it is nonzero
        unique_id = serial
        path += f"-{unique_id}"
    path += ".ipynb"  # And add the extension
    target += path

    new_param = Parameters(
        user=params.user,
        base_url=params.base_url,
        token=params.token,
        client=params.client,
        path=params.path,
        target=target,
        unique_id=unique_id,
    )
    LOGGER.debug("Continuing to redirect", param=new_param)
    return new_param


def _get_user_endpoint(base_url: str, user: str) -> str:
    return str(urljoin(base_url, f"/nb/user/{user}"))


def _get_code_from_template(client_path: str) -> str:
    client_path = "/".join(client_path.strip("/").split("/")[1:])
    code_template = _get_nbcheck_template()
    return Template(code_template).substitute(path=client_path)


def _get_nbcheck_template() -> str:
    return inspect.cleandoc(
        (Path(__file__).parent / "_github_notebook_payload.py").read_text()
    )
