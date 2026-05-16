import logging
from urllib.parse import quote_plus

from app.schemas.web_task import ActionDecision, ActionResult
from app.browser.base import BrowserProvider

logger = logging.getLogger(__name__)


async def execute_browser_action(
    provider: BrowserProvider, decision: ActionDecision
) -> ActionResult:
    """Execute a single ActionDecision on the browser provider.

    Handles ``search_web`` by converting the query to a Google search URL.
    All other action kinds are delegated to ``provider.execute_action``.
    """
    try:
        if decision.kind == "search_web":
            query = decision.value or ""
            url = f"https://www.google.com/search?q={quote_plus(query)}"
            logger.info(f"search_web → navigate to {url}")
            return await provider.navigate(url)

        return await provider.execute_action(decision)

    except Exception as e:
        logger.error(f"Browser action failed: {decision.kind} — {e}")
        return ActionResult(
            success=False,
            message=f"Browser action failed: {str(e)}",
        )
