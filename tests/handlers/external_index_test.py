"""Tests for the ghostwriter.handlers.external module and routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from ghostwriter.dependencies.config import config_dependency


@pytest.mark.asyncio
async def test_get_index(client: AsyncClient) -> None:
    """Test ``GET /ghostwriter/``."""
    response = await client.get("/ghostwriter/")
    assert response.status_code == 200
    data = response.json()
    metadata = data["metadata"]
    config = config_dependency.config
    assert metadata["name"] == config.name
    assert isinstance(metadata["version"], str)
    assert isinstance(metadata["description"], str)
    assert isinstance(metadata["repository_url"], str)
    assert isinstance(metadata["documentation_url"], str)
