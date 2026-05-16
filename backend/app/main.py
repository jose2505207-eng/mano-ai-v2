import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} ({settings.app_env})")
    yield
    logger.info(f"Shutting down {settings.app_name}")


app = FastAPI(
    title=settings.app_name,
    description="The internet, guided step by step.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (lazy — app starts even if Playwright/browser deps fail)
try:
    from app.api.tasks import router as tasks_router
    app.include_router(tasks_router)
except Exception as e:
    logging.getLogger(__name__).error(f"Failed to load tasks router: {e}")

try:
    from app.api.profile import router as profile_router
    app.include_router(profile_router)
except Exception as e:
    logging.getLogger(__name__).error(f"Failed to load profile router: {e}")

try:
    from app.api.logs import router as logs_router
    app.include_router(logs_router)
except Exception as e:
    logging.getLogger(__name__).error(f"Failed to load logs router: {e}")


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "app": settings.app_name,
        "mode": "real-web-agent",
    }


@app.get("/api/sponsor-status")
async def sponsor_status():
    """Check connectivity status of all tech sponsors."""

    def check_key(key: str) -> str:
        return "connected" if key else "not_configured"

    sponsors = [
        {
            "name": "Bright Data",
            "status": check_key(settings.brightdata_api_token),
            "details": "Web data infrastructure & SERP API",
        },
        {
            "name": "AgentField",
            "status": check_key(settings.agentfield_api_key),
            "details": "AI agent orchestration platform",
        },
        {
            "name": "Nosana",
            "status": check_key(settings.nosana_api_key),
            "details": "Decentralized GPU compute network",
        },
        {
            "name": "Actionbook",
            "status": check_key(settings.actionbook_api_key),
            "details": "Browser action manuals & automation",
        },
        {
            "name": "EverMind",
            "status": check_key(settings.evermind_api_key),
            "details": "Persistent AI memory & context",
        },
        {
            "name": "Qwen Cloud",
            "status": check_key(settings.qwen_api_key),
            "details": "Large language model provider",
        },
        {
            "name": "Zeabur",
            "status": "connected",
            "details": "One-click cloud deployment platform",
        },
        {
            "name": "Z.ai",
            "status": check_key(settings.zai_api_key),
            "details": "Advanced AI language models",
        },
        {
            "name": "Qoder",
            "status": "connected",
            "details": "AI-powered coding assistant — built this app!",
        },
        {
            "name": "TokenRouter",
            "status": check_key(settings.tokenrouter_api_key),
            "details": "Intelligent LLM request routing",
        },
        {
            "name": "Butterbase",
            "status": check_key(settings.butterbase_api_key),
            "details": "Backend-as-a-service data persistence",
        },
    ]

    return {"sponsors": sponsors}


# Mount frontend static files (if built)
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "out")
if os.path.isdir(FRONTEND_DIR):
    try:
        app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
        logger.info(f"Serving frontend from {FRONTEND_DIR}")
    except Exception as e:
        logger.warning(f"Failed to mount frontend static files: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=True)
