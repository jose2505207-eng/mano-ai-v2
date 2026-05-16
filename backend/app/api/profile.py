import logging
from fastapi import APIRouter
from app.schemas.web_task import UserProfile
from app.memory.store import load_profile, save_profile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["profile"])


@router.get("/profile", response_model=UserProfile)
async def get_profile():
    """Get the user's profile."""
    return load_profile()


@router.post("/profile", response_model=UserProfile)
async def update_profile(profile: UserProfile):
    """Update the user's profile."""
    save_profile(profile)
    logger.info(f"Profile updated for: {profile.full_name}")
    return profile
