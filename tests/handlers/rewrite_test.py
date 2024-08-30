"""Tests for the ghostwriter.handlers.external module and routes."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from ..support.gafaelfawr import MockGafaelfawr


@pytest.mark.asyncio
async def test_get_index(
    client: AsyncClient, mock_gafaelfawr: MockGafaelfawr
) -> None:
    """Test ``GET /ghostwriter/rewrite``."""
    user = mock_gafaelfawr.get_test_user()
    response = await client.get(
        "/ghostwriter/rewrite/tutorials/notebook1", headers=user.to_headers()
    )
    assert response.status_code == 307
