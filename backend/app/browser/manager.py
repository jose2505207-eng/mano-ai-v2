import logging

from .base import BrowserProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_playwright_provider():
    from .playwright_provider import PlaywrightProvider
    return PlaywrightProvider


def _get_actionbook_provider():
    from .actionbook_provider import ActionbookProvider
    return ActionbookProvider


class BrowserManager:
    """Manages browser provider selection and lifecycle.

    Resolution order:
      1. Actionbook — if ``browser_provider == "actionbook"`` and an API key
         is configured.
      2. Playwright — always available as the default fallback.
    """

    def __init__(self) -> None:
        self._provider: BrowserProvider | None = None

    async def get_provider(self) -> BrowserProvider:
        """Return the active provider, lazily initialising on first call."""
        if self._provider:
            return self._provider

        # Try Actionbook first if configured
        if settings.browser_provider == "actionbook" and settings.actionbook_api_key:
            try:
                ActionbookProvider = _get_actionbook_provider()
                provider = ActionbookProvider()
                await provider.launch()
                self._provider = provider
                logger.info("Using Actionbook browser provider")
                return provider
            except Exception as e:
                logger.warning(
                    f"Actionbook failed, falling back to Playwright: {e}"
                )

        # Default to Playwright
        PlaywrightProvider = _get_playwright_provider()
        provider = PlaywrightProvider()
        await provider.launch()
        self._provider = provider
        logger.info("Using Playwright browser provider")
        return provider

    async def close(self) -> None:
        """Shut down the active provider and release resources."""
        if self._provider:
            try:
                await self._provider.close()
            except Exception as e:
                logger.error(f"Error closing browser provider: {e}")
            finally:
                self._provider = None
