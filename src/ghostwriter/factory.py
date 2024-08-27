"""Component factory and process-wide status for ghostwriter."""

from __future__ import annotations

import structlog
import yaml
from httpx import AsyncClient
from safir.slack.webhook import SlackWebhookClient
from structlog.stdlib import BoundLogger

from .config import config

__all__ = ["Factory", "ProcessContext"]


class ProcessContext:
    """Per-process application context.

    This object caches all of the per-process singletons that can be reused
    for every request.

    Parameters
    ----------
    http_client
        Shared HTTP client.

    Attributes
    ----------
    http_client
        Shared HTTP client.

    base_url
        Base URL for the application; read from config.

    mapping
        Rewrite mapping; read from file specified in config.
    """

    def __init__(self, http_client: AsyncClient) -> None:
        self.http_client = http_client
        self.logger = structlog.get_logger("ghostwriter")
        self.base_url = config.environment_url
        self.reload_map()

    def reload_map(self) -> None:
        if config.mapping_file is None:
            raise RuntimeError("Cannot proceed without mapping file")
        with config.mapping_file.open() as fp:
            self.mapping = yaml.safe_load(fp)

    async def aclose(self) -> None:
        """Clean up a process context.

        Called before shutdown to free resources.
        """


class Factory:
    """Component factory for ghostwriter.

    Uses the contents of a `ProcessContext` to construct the components of an
    application on demand.

    Parameters
    ----------
    context
        Shared process context.

    Attributes
    ----------
    context
        Shared process context.
    """

    def __init__(
        self,
        context: ProcessContext,
        logger: BoundLogger | None = None,
        user: str | None = None,
    ) -> None:
        self.context = context
        self._logger = (
            logger if logger else structlog.get_logger("ghostwriter")
        )
        self._user = user

    def create_slack_webhook_client(self) -> SlackWebhookClient | None:
        """Create a Slack webhook client if configured for Slack alerting.

        Returns
        -------
        SlackWebhookClient or None
            Newly-created Slack client, or `None` if Slack alerting is not
            configured.
        """
        if not config.alert_hook:
            return None
        return SlackWebhookClient(
            str(config.alert_hook), "Ghostwriter", self._logger
        )

    def set_logger(self, logger: BoundLogger) -> None:
        """Replace the internal logger.

        Used by the context dependency to update the logger for all
        newly-created components when it's rebound with additional context.

        Parameters
        ----------
        logger
            New logger.
        """
        self._logger = logger
