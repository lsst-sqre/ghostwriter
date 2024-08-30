"""Test mapping model."""

import pytest
import yaml

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
    )
    res = await routemap.resolve(params)
    assert res == (
        "https://data.example.com/nb/user/rachel/lab/tree/notebook05.ipynb"
    )
