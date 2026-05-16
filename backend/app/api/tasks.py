import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas.web_task import WebTaskRun, UserProfile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class CreateTaskRequest(BaseModel):
    task: str
    language: str = "en"
    start_url: str | None = None
    constraints: dict = {}
    profile: dict = {}


class ContinueTaskRequest(BaseModel):
    user_input: str | None = None
    approved: bool | None = None


@router.post("", response_model=WebTaskRun)
async def create_task(req: CreateTaskRequest):
    """Create and start a new web task."""
    from app.agents.run_web_task import start_web_task

    logger.info(f"Creating task: {req.task}")

    profile = None
    if req.profile:
        try:
            profile = UserProfile(**req.profile)
        except Exception:
            pass

    task_run = await start_web_task(
        task=req.task,
        language=req.language,
        profile=profile,
        constraints=req.constraints,
    )
    return task_run


@router.get("/{task_id}", response_model=WebTaskRun)
async def get_task(task_id: str):
    """Get current state of a task."""
    from app.agents.run_web_task import get_task_state

    state = get_task_state(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="Task not found")
    return state


@router.post("/{task_id}/continue", response_model=WebTaskRun)
async def continue_task(task_id: str, req: ContinueTaskRequest):
    """Continue a paused task with user input or approval."""
    from app.agents.run_web_task import get_orchestrator

    orch = get_orchestrator(task_id)
    if not orch:
        raise HTTPException(status_code=404, detail="Task not found")

    if req.approved is not None:
        orch.resume_with_approval(req.approved)
    elif req.user_input is not None:
        orch.resume_with_input(req.user_input)
    else:
        raise HTTPException(status_code=400, detail="Must provide user_input or approved")

    # Brief wait for state update
    import asyncio
    await asyncio.sleep(0.2)

    return orch.task_run


@router.post("/{task_id}/stop")
async def stop_task(task_id: str):
    """Stop a running task."""
    from app.agents.run_web_task import get_orchestrator

    orch = get_orchestrator(task_id)
    if not orch:
        raise HTTPException(status_code=404, detail="Task not found")

    orch.stop()
    return {"status": "stopped", "task_id": task_id}


@router.get("/{task_id}/snapshot")
async def get_snapshot(task_id: str):
    """Get the latest browser snapshot for a task."""
    from app.agents.run_web_task import get_task_state

    state = get_task_state(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="Task not found")

    # Return latest step's screenshot if available
    if state.steps:
        last_step = state.steps[-1]
        if last_step.result and last_step.result.screenshot:
            return {
                "screenshot": last_step.result.screenshot,
                "url": state.current_url,
                "step_number": last_step.step_number,
            }

    return {"screenshot": None, "url": state.current_url, "step_number": 0}


@router.post("/{task_id}/step")
async def manual_step(task_id: str):
    """Trigger a single step (for debugging)."""
    raise HTTPException(status_code=501, detail="Manual stepping not yet implemented")
