import json
import logging

from app.llm.router import llm_decide_json
from app.llm.prompts import INTENT_SYSTEM

logger = logging.getLogger(__name__)


async def parse_intent(task: str) -> dict:
    """Parse a user's task description into structured intent.

    Returns:
        dict with keys: task_type, search_query, start_url, constraints, language
    """
    try:
        result = await llm_decide_json(INTENT_SYSTEM, f"User task: {task}")
    except Exception as e:
        logger.warning(f"Intent parsing LLM call failed: {e}")
        result = {}

    # Ensure all expected keys exist with defaults
    return {
        "task_type": result.get("task_type", "general"),
        "search_query": result.get("search_query"),
        "start_url": result.get("start_url"),
        "constraints": result.get("constraints", {}),
        "language": result.get("language", "en"),
    }
