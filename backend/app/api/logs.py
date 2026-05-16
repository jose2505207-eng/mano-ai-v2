import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["logs"])


@router.get("/logs")
async def get_logs():
    """Get activity logs (task summaries)."""
    from app.agents.run_web_task import list_task_ids, get_task_state

    logs = []
    for task_id in list_task_ids():
        state = get_task_state(task_id)
        if state:
            logs.append({
                "task_id": state.task_id,
                "task": state.task,
                "status": state.status,
                "steps_count": len(state.steps),
                "final_answer": state.final_answer,
                "current_url": state.current_url,
            })
    return {"logs": logs}
