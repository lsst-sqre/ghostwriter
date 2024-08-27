"""Configuration definition."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings
from safir.logging import LogLevel, Profile

__all__ = [
    "Configuration",
    "config",
]


class Configuration(BaseSettings):
    """Configuration for ghostwriter."""

    alert_hook: HttpUrl | None = Field(
        None,
        title="Slack webhook URL used for sending alerts",
        description=(
            "An https URL, which should be considered secret. If not set or"
            " set to `None`, this feature will be disabled."
        ),
        validation_alias="GHOSTWRITER_ALERT_HOOK",
        examples=["https://slack.example.com/ADFAW1452DAF41/"],
    )

    environment_url: HttpUrl | None = Field(
        None,
        title="Base URL of the Science Platform environment",
        description=(
            "Used to create URLs to other services. This is only optional"
            " to make writing the test suite easier. If it is not set to a"
            " valid URL, ghostwriter will abort during startup."
        ),
        validation_alias="GHOSTWRITER_ENVIRONMENT_URL",
        examples=["https://data.example.org/"],
    )

    mapping_file: Path | None = Field(
        None,
        title="Path to YAML file defining URL mappings",
        description=(
            "A YAML file containing a mapping of base routes to full URLs"
            " where '{user}' will be substituted with the user name. This is"
            " only optional to make writing the test suite easier.  If it is"
            " not set to a valid YAML file, ghostwriter will abort during"
            " startup."
        ),
        validation_alias="GHOSTWRITER_MAPPING_PATH",
        examples=["/etc/ghostwriter/config.yaml"],
    )

    name: str = Field(
        "ghostwriter",
        title="Name of application",
        description="Doubles as the root HTTP endpoint path.",
        validation_alias="GHOSTWRITER_NAME",
    )

    path_prefix: str = Field(
        "/ghostwriter",
        title="URL prefix for application API",
        validation_alias="GHOSTWRITER_PATH_PREFIX",
    )

    profile: Profile = Field(
        Profile.development,
        title="Application logging profile",
        validation_alias="GHOSTWRITER_LOGGING_PROFILE",
    )

    log_level: LogLevel = Field(
        LogLevel.INFO,
        title="Log level of the application's logger",
        validation_alias="GHOSTWRITER_LOG_LEVEL",
    )


config = Configuration()
"""Configuration for ghostwriter."""
