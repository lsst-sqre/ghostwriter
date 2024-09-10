"""Takes a portal query ID from the request path and calls the Lab endpoint
to template and write that query.  We assume there's already a running lab,
which we can he sure of by putting ensure_running_lab in before this in the
hooks.
"""

import inspect
from string import Template
from urllib.parse import urljoin

import structlog

from ..models.substitution import Parameters

LOGGER = structlog.get_logger("ghostwriter")


async def tutorial_on_demand(params: Parameters) -> Parameters | None:
    """Check out a particular tutorial notebook."""
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
    if serial != "0":
        # We had to change the filename and filename schema.
        # Return a modified Parameters object.
        pathcomp = params.path.split("/")
        pathcomp[-1] = "${path}-${unique_id}.ipynb"
        path = "/".join(pathcomp)
        unique_id = str(serial)
        LOGGER.debug("Continuing to redirect", path=path, unique_id=unique_id)
        return Parameters(
            user=params.user,
            base_url=params.base_url,
            token=params.token,
            client=params.client,
            path=path,
            unique_id=unique_id,
        )
    LOGGER.debug("Continuing to redirect; params unchanged")
    return None


def _get_user_endpoint(base_url: str, user: str) -> str:
    return str(urljoin(base_url, f"/nb/user/{user}"))


def _get_code_from_template(client_path: str) -> str:
    client_path = "/".join(client_path.strip("/").split("/")[1:])
    code_template = _get_nbcheck_template()
    return Template(code_template).substitute(path=client_path)


def _get_nbcheck_template() -> str:
    return inspect.cleandoc(
        """import os
        import requests
        from base64 import b64decode
        from datetime import datetime, timezone
        from pathlib import Path

        topdir = Path(os.environ['HOME']) / "notebooks" / "tutorials-on-demand"
        nb = topdir / "${path}.ipynb"
        nb_base = nb.name[:-(len(".ipynb"))]
        nbdir = nb.parent
        nbdir.mkdir(exist_ok=True)
        serial = 0
        while nb.exists():
            # Count up until we find an unused number to append to the name.
            serial += 1
            nb = nbdir / f"{nb_base}-{serial}.ipynb"

        # Retrieve notebook content from github.
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

        # Finally, print the value of ``serial``, which we will capture as
        # a notebook stream output to determine whether we need to modify
        # the path and unique_id in rewrite parameters.
        print(serial)
        """
    )
