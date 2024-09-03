"""Configuration definition."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Self

import yaml
from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from safir.logging import LogLevel, Profile

from .constants import ROUTING_PATH

__all__ = [
    "Configuration",
]


class Configuration(BaseSettings):
    """Configuration for ghostwriter."""

    alert_hook: Annotated[
        HttpUrl | None,
        Field(
            title="Slack webhook URL used for sending alerts",
            description=(
                "An https URL, which should be considered secret. If not set"
                " or set to `None`, this feature will be disabled."
            ),
            validation_alias="GHOSTWRITER_ALERT_HOOK",
            examples=["https://slack.example.com/ADFAW1452DAF41/"],
        ),
    ] = None

    environment_url: Annotated[
        HttpUrl | None,
        Field(
            title="Base URL of the Science Platform environment",
            description=(
                "Used to create URLs to other services. This is only optional"
                " to make writing the test suite easier. If it is not set to a"
                " valid URL, ghostwriter will abort during startup."
            ),
            validation_alias="GHOSTWRITER_ENVIRONMENT_URL",
            examples=["https://data.example.org/"],
        ),
    ] = HttpUrl("http://localhost:8080")

    mapping_file: Annotated[
        Path | None,
        Field(
            title="Path to YAML file defining URL mappings",
            description=(
                "A YAML file containing a mapping of base routes to full URLs"
                " where '{user}' will be substituted with the user name. This"
                " is only optional to make writing the test suite easier.  If"
                " it is not set to a valid YAML file, ghostwriter will abort"
                " during startup."
            ),
            validation_alias="GHOSTWRITER_MAPPING_PATH",
            examples=["/etc/ghostwriter/routing.yaml"],
        ),
    ] = ROUTING_PATH

    name: Annotated[
        str,
        Field(
            title="Name of application",
            description="Doubles as the root HTTP endpoint path.",
            validation_alias="GHOSTWRITER_NAME",
        ),
    ] = "ghostwriter"

    path_prefix: Annotated[
        str,
        Field(
            title="URL prefix for application API",
            validation_alias="GHOSTWRITER_PATH_PREFIX",
        ),
    ] = "/ghostwriter"

    profile: Annotated[
        Profile,
        Field(
            Profile.development,
            title="Application logging profile",
            validation_alias="GHOSTWRITER_LOGGING_PROFILE",
        ),
    ] = Profile.production

    log_level: Annotated[
        LogLevel,
        Field(
            title="Log level of the application's logger",
            validation_alias="GHOSTWRITER_LOG_LEVEL",
        ),
    ] = LogLevel.INFO

    model_config = SettingsConfigDict(populate_by_name=True)
    model_config["env_ignore_empty"] = True

    def to_yaml(self) -> str:
        """Produce a YAML document we could use for from_file.  Fortunately,
        JSON is YAML, so...
        """
        return self.model_dump_json()

    @classmethod
    def from_file(cls, path: Path) -> Self:
        """Load ghostwriter configuration from a YAML file.

        Parameters
        ----------
        path
            Path to the configuration file.
        """
        with path.open("r") as f:
            obj = yaml.safe_load(f)
            if obj is None:
                obj = {}
            return cls.model_validate(obj)
