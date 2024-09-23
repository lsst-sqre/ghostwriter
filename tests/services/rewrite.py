"""Test mapping model."""

import pytest
import structlog
import yaml
from rubin.nublado.client import NubladoClient
from rubin.nublado.client.models import User

from ghostwriter.config import Configuration
from ghostwriter.models.substitution import Parameters
from ghostwriter.models.v1.mapping import RouteCollection
from ghostwriter.services.rewrite import rewrite_request


@pytest.mark.asyncio
async def test_rewrite(config: Configuration) -> None:
    """Test rewriting a path."""
    assert config.mapping_file is not None
    with config.mapping_file.open() as f:
        contents = yaml.safe_load(f)
    routemap = RouteCollection.model_validate(contents)
    assert routemap.get_routes() == ["/tutorials/"]
    logger = structlog.get_logger("ghostwriter")
    params = Parameters(
        user="rachel",
        token="token-of-affection",
        path="tutorials/notebook05",
        base_url="https://data.example.com",
        client=NubladoClient(
            user=User(
                username="rachel",
                token="token-of-affection",
            ),
            base_url="https://data.example.com",
            logger=logger,
        ),
    )
    res = await rewrite_request(routemap, params, logger)
    assert res == (
        "https://data.example.com/nb/user/rachel/lab/tree/notebook05.ipynb"
    )
