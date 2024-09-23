import os
from base64 import b64decode
from pathlib import Path

import requests

path = "${path}"
branch = ""
branch_components = path.split("@")
if len(branch_components) > 2:
    raise RuntimeError(f"more than one '@' found on path '{path}'")
if len(branch_components) == 2:
    path = branch_components[0]
    branch = branch_components[1]
path_components = path.split("/")
if len(path_components) < 4:
    raise RuntimeError(f"host/owner/repo/file not found in '{path}'")
host = path_components[0]
owner = path_components[1]
repo = path_components[2]
rest = "/".join(path_components[3:])
# Filter by allowed hosts--just "github.com", because we use the GH
# API
if host != "github.com":
    raise RuntimeError(f"'{host}' not 'github.com'")
# Filter by allowed owning organizations
allowed_owners = ("lsst", "lsst-dm", "lsst-sqre", "lsst-ts", "rubin-dp0")
if owner not in allowed_owners:
    raise RuntimeError(f"{owner} not in {allowed_owners}")
# Canonicalize path
if path.endswith(".ipynb"):
    path = path[: -(len(".ipynb"))]
    rest = rest[: -(len(".ipynb"))]
topdir = Path(os.environ["HOME"]) / "notebooks" / "on-demand"
nbdir = (topdir / path).parent
nb_base = Path(path).name
nb = Path(nbdir / f"{nb_base}.ipynb")
nbdir.mkdir(exist_ok=True, parents=True)
serial = 0
while nb.exists():
    # Count up until we find an unused number to append to the name.
    serial += 1
    nb = nbdir / f"{nb_base}-{serial}.ipynb"

# Retrieve notebook content from github.
url = f"https://api.github.com/repos/{owner}/{repo}/contents/{rest}"
url += ".ipynb"
if branch:
    url += f"?ref={branch}"
r = requests.get(url, timeout=10)
obj = r.json()
content_b64 = obj["content"]
# Turn that back into a UTF-8 string
content = b64decode(content_b64).decode()

# And write it into place
nb.write_text(content)

# Finally, print the value of ``serial``, which we will capture as
# a notebook stream output to determine whether we need to modify
# the path and unique_id in rewrite parameters.
print(serial)
