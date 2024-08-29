"""Test fixtures for ghostwriter tests."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest_asyncio
import yaml
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import ghostwriter
from ghostwriter.config import Configuration
from ghostwriter.main import create_app


@pytest_asyncio.fixture(scope="session")
async def app() -> AsyncIterator[FastAPI]:
    """Return a configured test application.

    Writes configuration to a file within a session-scoped temporary
    directory and patches it to find its routing file there, then
    changes GHOSTWRITER_CONFIGURATION_PATH to point there.

    Wraps the application in a lifespan manager so that startup and
    shutdown events are sent during test execution.
    """
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

        os.environ["GHOSTWRITER_CONFIGURATION_PATH"] = str(newconfig)

        gw_app = create_app()
        async with LifespanManager(gw_app):
            yield gw_app


@pytest_asyncio.fixture(scope="session")
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Return an ``httpx.AsyncClient`` configured to talk to the test app."""
    config = ghostwriter.dependencies.config.config_dependency.config
    async with AsyncClient(
        transport=ASGITransport(app=app),
        # Pydantic URLs and HTTPx URLs aren't the same thing, but it will
        # take a string in the constructor.
        base_url=str(config.environment_url),
        follow_redirects=False,
    ) as client:
        yield client
