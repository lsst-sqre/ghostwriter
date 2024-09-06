"""Test mapping model."""

import pytest
import structlog
import yaml
from rubin.nublado.client import NubladoClient
from rubin.nublado.client.models.user import AuthenticatedUser

from ghostwriter.config import Configuration
from ghostwriter.models.substitution import Parameters
from ghostwriter.models.v1.mapping import RouteMap


@pytest.mark.asyncio
async def test_mapping(config: Configuration) -> None:
    """Test mapping methods."""
    assert config.mapping_file is not None
    with config.mapping_file.open() as f:
        contents = yaml.safe_load(f)
    routemap = RouteMap.model_validate(contents)
    assert routemap.get_routes() == ["/tutorials/"]
    params = Parameters(
        user="rachel",
        token="token-of-affection",
        path="tutorials/notebook05",
        base_url="https://data.example.com",
        client=NubladoClient(
            user=AuthenticatedUser(
                username="rachel",
                uidnumber=1101,
                gidnumber=1101,
                scopes=["exec:notebook", "read:tap", "exec:portal"],
                token="token-of-affection",
            ),
            base_url="https://data.example.com",
            logger=structlog.get_logger("ghostwriter"),
        ),
    )
    res = await routemap.resolve(params)
    assert res == (
        "https://data.example.com/nb/user/rachel/lab/tree/notebook05.ipynb"
    )
