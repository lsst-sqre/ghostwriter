"""Tests for ghostwriter's configuration."""

from pathlib import Path

import pytest

from ghostwriter.config import Configuration


def test_empty_file() -> None:
    """Test that an empty file imports correctly."""
    emptyfile = Path(__file__).parent / "support" / "config-vacuous.yaml"
    cfg = Configuration.from_file(emptyfile)
    assert cfg is not None
    assert str(cfg.environment_url) == "http://localhost:8080/"


def test_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    emptyfile = Path(__file__).parent / "support" / "config-vacuous.yaml"
    monkeypatch.setenv(
        "GHOSTWRITER_ENVIRONMENT_URL", "https://data.example.org"
    )
    cfg = Configuration.from_file(emptyfile)
    assert cfg is not None
    assert str(cfg.environment_url) == "https://data.example.org/"
