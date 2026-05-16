import logging

from app.schemas.web_task import UserProfile
from app.memory.store import load_profile, save_profile

logger = logging.getLogger(__name__)


def get_user_profile() -> UserProfile:
    """Load the user's profile from persistent storage."""
    profile = load_profile()
    logger.info(f"Loaded profile for: {profile.full_name or 'anonymous'}")
    return profile


def update_user_profile(profile: UserProfile) -> None:
    """Save an updated user profile to persistent storage."""
    save_profile(profile)
    logger.info(f"Saved profile for: {profile.full_name or 'anonymous'}")
