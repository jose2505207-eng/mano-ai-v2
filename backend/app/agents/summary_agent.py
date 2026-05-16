import logging

from app.schemas.web_task import WebTaskStep
from app.llm.router import llm_decide
from app.llm.prompts import SUMMARY_SYSTEM_EN, SUMMARY_SYSTEM_ES

logger = logging.getLogger(__name__)


async def summarize_task(
    task: str, steps: list[WebTaskStep], language: str = "en"
) -> str:
    """Generate a human-readable summary of a completed task."""
    prompt = SUMMARY_SYSTEM_ES if language == "es" else SUMMARY_SYSTEM_EN

    step_descriptions: list[str] = []
    for s in steps:
        desc = f"Step {s.step_number}: {s.decision.kind}"
        if s.decision.user_visible_message:
            desc += f" — {s.decision.user_visible_message}"
        if s.result:
            mark = "\u2713" if s.result.success else "\u2717"
            desc += f" \u2192 {mark} {s.result.message}"
        step_descriptions.append(desc)

    context = f"Task: {task}\n\nSteps:\n" + "\n".join(step_descriptions)

    try:
        return await llm_decide(prompt, context)
    except Exception as e:
        logger.warning(f"Summary LLM failed: {e}")
        if language == "es":
            return f"Tarea completada con {len(steps)} pasos."
        return f"Task completed with {len(steps)} steps."
