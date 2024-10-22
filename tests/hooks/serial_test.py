"""Test the filename construction from serial bit of the github hook."""

import json
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient
from rubin.nublado.client import NubladoClient
from rubin.nublado.client.models import User

from ghostwriter.config import Configuration
from ghostwriter.hooks.github_notebook import _get_new_params
from ghostwriter.models.substitution import Parameters

COMMON_PREFIX = (
    "https://data.example.org/nb/user/rachel/lab/tree/notebooks"
    "/on-demand/github.com/lsst-sqre/system-test/Firefly"
)


@pytest_asyncio.fixture
def std_params(config: Configuration, client: AsyncClient) -> Parameters:
    user_objs = json.loads(
        (Path(__file__).parent.parent / "support" / "users.json").read_text()
    )
    token = next(iter(user_objs.keys()))
    username = user_objs[token]["username"]
    user = User(username=username, token=token)
    nc = NubladoClient(user=user, base_url=str(config.environment_url))
    return Parameters(
        user=user.username,
        base_url=str(config.environment_url),
        token=token,
        client=nc,
        path="notebooks/github.com/lsst-sqre/system-test/Firefly",
        target="inconsequential",
        unique_id=None,
    )


@pytest.mark.asyncio
async def test_basic_rewrite(std_params: Parameters) -> None:
    new_p = _get_new_params("0", std_params)
    expected = f"{COMMON_PREFIX}.ipynb"
    assert new_p.target == expected


@pytest.mark.asyncio
async def test_serial_rewrite(std_params: Parameters) -> None:
    new_p = _get_new_params("3", std_params)
    expected = f"{COMMON_PREFIX}-3.ipynb"
    assert new_p.target == expected


@pytest.mark.asyncio
async def test_strip_branch(std_params: Parameters) -> None:
    inp = Parameters(
        user=std_params.user,
        base_url=std_params.base_url,
        token=std_params.token,
        client=std_params.client,
        path=f"{std_params.path}@prod",
        target=std_params.target,
        unique_id=std_params.unique_id,
    )
    new_p = _get_new_params("0", inp)
    expected = f"{COMMON_PREFIX}.ipynb"
    assert new_p.target == expected
