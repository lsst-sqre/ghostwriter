"""Test fixtures for ghostwriter tests."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import pytest_asyncio
import respx
import yaml
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from ghostwriter.config import Configuration
from ghostwriter.dependencies.context import context_dependency
from ghostwriter.main import create_app

from .support.gafaelfawr import (
    GafaelfawrUserInfo,
    MockGafaelfawr,
    register_mock_gafaelfawr,
)


@pytest.fixture(scope="session")
def test_env() -> Iterator[Path]:
    with TemporaryDirectory() as td:
        fake_root = Path(td)

        input_dir = Path(__file__).parent / "support"
        output_dir = fake_root / "etc" / "ghostwriter"
        output_dir.mkdir(parents=True)
        mapping = (input_dir / "routing.yaml").read_text()
        mapping_file = output_dir / "routing.yaml"
        mapping_file.write_text(mapping)
        with (input_dir / "config.yaml").open() as f:
            config_contents = yaml.safe_load(f)
        config = Configuration.model_validate(config_contents)
        config.mapping_file = mapping_file
        config_yaml = config.to_yaml()
        newconfig = output_dir / "config.yaml"
        newconfig.write_text(config_yaml)

        yield newconfig


@pytest.fixture(scope="session")
def config(test_env: Path) -> Configuration:
    with test_env.open() as f:
        return Configuration.model_validate(yaml.safe_load(f))


@pytest.fixture
def mock_gafaelfawr(
    respx_mock: respx.Router, config: Configuration
) -> MockGafaelfawr:
    user_objs = json.loads(
        (Path(__file__).parent / "support" / "users.json").read_text()
    )
    users = {
        t: GafaelfawrUserInfo.model_validate(u) for t, u in user_objs.items()
    }

    return register_mock_gafaelfawr(
        respx_mock,
        str(config.environment_url),
        users,
    )


@pytest_asyncio.fixture
async def app(
    test_env: Path, mock_gafaelfawr: MockGafaelfawr
) -> AsyncIterator[FastAPI]:
    """Return a configured test application.

    Writes configuration to a file within a session-scoped temporary
    directory and patches it to find its routing file there, then
    changes GHOSTWRITER_CONFIGURATION_PATH to point there.

    Wraps the application in a lifespan manager so that startup and
    shutdown events are sent during test execution.
    """
    os.environ["GHOSTWRITER_CONFIGURATION_PATH"] = str(test_env)
    gw_app = create_app()
    await context_dependency.initialize()
    async with LifespanManager(gw_app):
        yield gw_app


@pytest_asyncio.fixture
async def client(
    app: FastAPI, config: Configuration
) -> AsyncIterator[AsyncClient]:
    """Return an ``httpx.AsyncClient`` configured to talk to the test app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        # Pydantic URLs and HTTPx URLs aren't the same thing, but it will
        # take a string in the constructor.
        base_url=str(config.environment_url),
        follow_redirects=False,
    ) as client:
        yield client
