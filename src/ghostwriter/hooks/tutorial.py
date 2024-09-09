"""Takes a portal query ID from the request path and calls the Lab endpoint
to template and write that query.  We assume there's already a running lab,
which we can he sure of by putting ensure_running_lab in before this in the
hooks.
"""

import inspect
from string import Template
from urllib.parse import urljoin

import structlog
from httpx import AsyncClient

from ..models.substitution import Parameters

LOGGER = structlog.get_logger("ghostwriter")


async def tutorial_on_demand(params: Parameters) -> None:
    """Check out a particular tutorial notebook."""
    client = params.client
    LOGGER.debug("Logging in to hub", user=params.user)
    await client.auth_to_hub()
    LOGGER.debug("Authenticating to lab")
    await client.auth_to_lab()
    async with client.open_lab_session() as lab_session:
        code = _get_code_from_template(params.path)
        # once nublado-seeds is merged, we could have
        # something like _get_code_from_nublado_seeds(params.client.http)
        LOGGER.debug("Code for execution in Lab context", code=code)
        await lab_session.run_python(code)
    LOGGER.debug("Continuing to redirect")


def _get_user_endpoint(base_url: str, user: str) -> str:
    return str(urljoin(base_url, f"/nb/user/{user}"))


def _get_code_from_template(client_path: str) -> str:
    client_path = "/".join(client_path.strip("/").split("/")[1:])
    code_template = _get_nbcheck_template()
    return Template(code_template).substitute(path=client_path)


async def _get_code_from_nublado_seeds(http_client: AsyncClient) -> str:
    """Get the templated notebook from nublado-seeds, and then extract and
    return the code contents.
    """
    # These are constant for this sort of query
    org = "lsst-sqre"
    repo = "nublado-seeds"
    directory = "tutorials-on-demand"
    notebook = "fetch"

    nb_url = f"github/{org}/{repo}/{directory}/{notebook}"

    resp = await http_client.get(nb_url)
    obj = resp.json()
    return "\n".join(
        x["source"] for x in obj["cells"] if x["cell_type"] == "code"
    )


def _get_nbcheck_template() -> str:
    # This should probably go into nublado-seeds.  At least it's an isolated
    # function, easy to swap out.
    return inspect.cleandoc(
        """import os
        import requests
        from base64 import b64decode
        from datetime import datetime, timezone
        from pathlib import Path

        topdir = Path(os.environ['HOME']) / "notebooks" / "tutorials-on-demand"
        nb = topdir / "${path}.ipynb"
        nb.parent.mkdir(exist_ok=True)
        if nb.exists():
            # Move extant notebook aside
            now = datetime.now(timezone.utc).isoformat()
            nbdir = nb.parent
            newname = Path("${path}").name + "-" + now + ".ipynb"
            nb.rename(nbdir / newname)

        # Retrieve content.

        # Owner, repo, and branch are constant in this context.
        owner = "rubin-dp0"
        repo = "tutorial-notebooks"
        branch = "prod"
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/${path}"
        url += f".ipynb?ref={branch}"
        r=requests.get(url)
        obj=r.json()
        content_b64 = obj["content"]
        # Turn that back into a UTF-8 string
        content = b64decode(content_b64).decode()

        # And write it into place
        nb.write_text(content)
        """
    )
