"""Takes a GitHub notebook repo/owner/path from the request path and
puts it into the user's lab environment.  We assume there's already a running
lab, which we can he sure of by putting ensure_running_lab in before this in
the hooks.
"""

import inspect
from string import Template
from urllib.parse import urljoin

import structlog

from ..models.substitution import Parameters

LOGGER = structlog.get_logger("ghostwriter")


async def github_notebook(params: Parameters) -> Parameters | None:
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
    if serial and serial != "0" and params.target is not None:
        #
        # params.target is never None, because it's injected by run_hooks(),
        # but mypy doesn't know that.
        #
        # We had to change the filename and filename schema.
        # Return a modified Parameters object.
        #
        targetcomp = params.target.split("/")
        targetcomp[-1] = "${path}-${unique_id}.ipynb"
        target = "/".join(targetcomp)
        unique_id = str(serial)
        LOGGER.debug(
            "Continuing to redirect", target=target, unique_id=unique_id
        )
        return Parameters(
            user=params.user,
            base_url=params.base_url,
            token=params.token,
            client=params.client,
            path=params.path,
            target=target,
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

        path = "${path}"
        branch = ""
        branch_components = path.split("@")
        if len(branch_components) > 2:
            raise RuntimeError(f"more than one '@' found on path '{path}'")
        if len(branch_components) == 2:
            path = branch_components[0]
            branch = branch_components[1]
        path_components = path.split("/")
        if len(path_components) < 3:
            raise RuntimeError(f"owner/repo/file not found in '{path}'")
        owner = path[0]
        repo = path[1]
        # Filter by allowed owning organizations
        allowed = ("lsst", "lsst-dm", "lsst-sqre", "lsst-ts", "rubin-dp0")
        if owner not in allowed:
            raise RuntimeError(f"{owner} not in {allowed}")
        # Canonicalize path
        if path.endswith(".ipynb"):
            path=path[:len(".ipynb")]
        topdir = (Path(os.environ['HOME']) / "notebooks" /
                  "on-demand" / "github.com")
        nbdir = (topdir / path).parent
        nb_base = Path(path).name
        nb = Path(nbdir / f"{nb_base}.ipynb")
        nbdir.mkdir(exist_ok=True)
        serial = 0
        while nb.exists():
            # Count up until we find an unused number to append to the name.
            serial += 1
            nb = nbdir / f"{nb_base}-{serial}.ipynb"

        # Retrieve notebook content from github.
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        url += ".ipynb"
        if branch:
            url += f"?ref={branch}"
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
