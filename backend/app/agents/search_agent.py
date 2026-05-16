import logging
from urllib.parse import quote_plus

from app.llm.router import llm_decide_json
from app.llm.prompts import SEARCH_SYSTEM

logger = logging.getLogger(__name__)


async def find_start_url(task: str, intent: dict) -> str:
    """Determine the best starting URL for a task.

    Resolution order:
      1. Direct URL from intent (if the user provided one).
      2. LLM-suggested URL.
      3. Google search fallback.
    """
    # If intent already has a URL
    if intent.get("start_url"):
        logger.info(f"Using direct URL from intent: {intent['start_url']}")
        return intent["start_url"]

    # Ask LLM for best URL
    try:
        result = await llm_decide_json(
            SEARCH_SYSTEM, f"Task: {task}\nIntent: {intent}"
        )
        if result.get("url"):
            logger.info(f"LLM suggested URL: {result['url']}")
            return result["url"]
    except Exception as e:
        logger.warning(f"Search agent LLM failed: {e}")

    # Fallback: Google search
    query = intent.get("search_query") or task
    fallback_url = f"https://www.google.com/search?q={quote_plus(query)}"
    logger.info(f"Falling back to Google search: {fallback_url}")
    return fallback_url
