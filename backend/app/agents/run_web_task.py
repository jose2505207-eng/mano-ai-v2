"""Async task runner wrapper for Mano AI web tasks.

Provides a fire-and-forget interface for starting tasks in the background
while returning the initial :class:`WebTaskRun` state immediately.
"""

import asyncio
import logging

from app.schemas.web_task import WebTaskRun, UserProfile

from .orchestrator import Orchestrator

logger = logging.getLogger(__name__)

# Global store of active orchestrators (keyed by task_id)
_active_tasks: dict[str, Orchestrator] = {}


async def start_web_task(
    task: str,
    language: str = "en",
    profile: UserProfile | None = None,
    constraints: dict | None = None,
) -> WebTaskRun:
    """Start a new web task in the background.

    Returns the initial :class:`WebTaskRun` immediately; the orchestrator
    continues running and updates the object in-place as it progresses.
    """
    orchestrator = Orchestrator()

    async def _run() -> None:
        try:
            await orchestrator.run(task, language, profile, constraints)
        except Exception as e:
            logger.error(f"Task execution failed: {e}", exc_info=True)
            if orchestrator.task_run:
                orchestrator.task_run.status = "failed"
                orchestrator.task_run.final_answer = f"Task failed: {str(e)}"

    # Create a placeholder task run to return immediately.
    # The orchestrator.run() call will replace it with the real one.
    orchestrator.task_run = WebTaskRun(
        task_id="pending",
        task=task,
        status="running",
    )

    # Fire-and-forget — let the orchestrator run in the background
    loop = asyncio.get_running_loop()
    loop.create_task(_run())

    # Brief wait for the task_id to be assigned by run()
    await asyncio.sleep(0.1)

    task_id = orchestrator.task_run.task_id or "pending"
    _active_tasks[task_id] = orchestrator

    return orchestrator.task_run


def get_orchestrator(task_id: str) -> Orchestrator | None:
    """Get an active orchestrator by task ID."""
    return _active_tasks.get(task_id)


def get_task_state(task_id: str) -> WebTaskRun | None:
    """Get the current state of a task."""
    orch = _active_tasks.get(task_id)
    if orch and orch.task_run:
        return orch.task_run
    return None


def list_task_ids() -> list[str]:
    """List all active task IDs."""
    return list(_active_tasks.keys())
