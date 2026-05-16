import logging

from app.schemas.web_task import ActionDecision, BrowserSnapshot, WebTaskStep
from app.llm.router import llm_decide_json
from app.llm.prompts import CRITIC_SYSTEM

logger = logging.getLogger(__name__)


async def evaluate_decision(
    decision: ActionDecision,
    snapshot: BrowserSnapshot,
    task: str,
    history: list[WebTaskStep],
) -> dict:
    """Evaluate a proposed action for quality.

    Returns:
        ``{"approved": bool, "reason": str, "suggested_alternative": dict | None}``

    Performs both heuristic (fast, no LLM) and LLM-based evaluation.
    """

    # ------------------------------------------------------------------
    # Heuristic checks (fast, no LLM needed)
    # ------------------------------------------------------------------

    # 1. Low confidence check
    if decision.confidence < 0.3:
        return {
            "approved": False,
            "reason": f"Confidence too low ({decision.confidence}). Agent seems uncertain.",
            "suggested_alternative": None,
        }

    # 2. Loop detection (same URL navigated 2+ times)
    if decision.kind == "navigate" and history:
        nav_urls = [
            s.decision.url or s.decision.value
            for s in history
            if s.decision.kind == "navigate" and (s.decision.url or s.decision.value)
        ]
        target = decision.url or decision.value
        if target and nav_urls.count(target) >= 2:
            return {
                "approved": False,
                "reason": f"Already navigated to {target} twice — likely loop.",
                "suggested_alternative": None,
            }

    # 3. Stuck detection (3+ stuck/ask_user in a row)
    if history and len(history) >= 3:
        last_3 = [s.decision.kind for s in history[-3:]]
        if all(k in ("stuck", "ask_user") for k in last_3):
            return {
                "approved": False,
                "reason": "Agent appears stuck — 3 consecutive non-progress actions.",
                "suggested_alternative": None,
            }

    # 4. Progress check — warn if many steps with no meaningful interaction
    if len(history) >= 10:
        recent_clicks = sum(
            1 for s in history[-5:] if s.decision.kind == "click"
        )
        recent_fills = sum(
            1 for s in history[-5:] if s.decision.kind == "fill"
        )
        if recent_clicks == 0 and recent_fills == 0:
            logger.warning(
                "No clicks or fills in last 5 steps — possible stall"
            )

    # ------------------------------------------------------------------
    # LLM-based evaluation (for complex decisions)
    # ------------------------------------------------------------------
    try:
        last_kinds = [s.decision.kind for s in history[-3:]] if history else []
        context = (
            f"Task: {task}\n"
            f"Current URL: {snapshot.url}\n"
            f"Page title: {snapshot.title}\n"
            f"Steps taken: {len(history)}\n"
            f"Proposed action: {decision.model_dump_json()}\n"
            f"Last 3 actions: {last_kinds}"
        )

        result = await llm_decide_json(CRITIC_SYSTEM, context)
        return {
            "approved": result.get("approved", True),
            "reason": result.get("reason", "LLM critic approved"),
            "suggested_alternative": result.get("suggested_alternative"),
        }
    except Exception as e:
        logger.warning(f"Critic LLM failed, defaulting to approve: {e}")
        return {
            "approved": True,
            "reason": "Critic unavailable — defaulting to approve",
            "suggested_alternative": None,
        }
