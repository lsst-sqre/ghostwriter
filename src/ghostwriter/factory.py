"""Component factory and process-wide status for ghostwriter."""

from __future__ import annotations

import structlog
import yaml
from safir.slack.webhook import SlackWebhookClient
from structlog.stdlib import BoundLogger

from .dependencies.config import config_dependency
from .models.v1.mapping import RouteMap
from .services.rsp_client_manager import RSPClientManager
from .storage.gafaelfawr import GafaelfawrManager

__all__ = ["Factory", "ProcessContext"]


class ProcessContext:
    """Per-process application context.

    This object caches all of the per-process singletons that can be reused
    for every request.

    Attributes
    ----------
    base_url
        Base URL for the application; read from config.

    config
        Application config.

    mapping
        Rewrite mapping; read from file specified in config.

    gafaelfawr_manager
        Cache for token-to-user-and-capability mappings.

    rsp_client_manager
        Cache for token-to-rsp-client mapping.
    """

    def __init__(self) -> None:
        self.logger = structlog.get_logger("ghostwriter")
        self.config = config_dependency.config
        self.base_url = self.config.environment_url
        if self.base_url is None:
            raise RuntimeError("config.environent_url must be set")
        self.gafaelfawr_manager = GafaelfawrManager(base_url=self.base_url)
        self.rsp_client_manager = RSPClientManager(
            base_url=self.base_url,
            logger=self.logger,
            gafaelfawr_manager=self.gafaelfawr_manager,
        )
        self.reload_map()

    def reload_map(self) -> None:
        if self.config.mapping_file is None:
            raise RuntimeError("Cannot proceed without mapping file")
        with self.config.mapping_file.open() as fp:
            map_obj = yaml.safe_load(fp)
            self.mapping = RouteMap.model_validate(map_obj)

    async def aclose(self) -> None:
        """Clean up a process context.

        Called before shutdown to free resources.
        """
        await self.rsp_client_manager.aclose()


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
    ) -> None:
        self.context = context
        self._logger = (
            logger if logger else structlog.get_logger("ghostwriter")
        )

    def create_slack_webhook_client(self) -> SlackWebhookClient | None:
        """Create a Slack webhook client if configured for Slack alerting.

        Returns
        -------
        SlackWebhookClient or None
            Newly-created Slack client, or `None` if Slack alerting is not
            configured.
        """
        if not self.context.config.alert_hook:
            return None
        return SlackWebhookClient(
            str(self.context.config.alert_hook), "Ghostwriter", self._logger
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
