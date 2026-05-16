"""Simple profile persistence for Mano AI.

Profiles are stored as JSON on disk. The runtime profile is preferred over
the template when both exist.
"""

import json
import os
from pathlib import Path

from ..schemas.web_task import UserProfile

_DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
_RUNTIME_PROFILE_PATH = _DATA_DIR / "profile.json"
_TEMPLATE_PROFILE_PATH = _DATA_DIR / "profile.template.json"

_BLOCKED_AUTO_FILL_FIELDS: frozenset[str] = frozenset({
    "payment_card",
    "ssn",
    "social_security_number",
    "passport",
    "driver_license",
    "password",
    "medical",
    "legal",
})


def load_profile() -> UserProfile:
    """Load the user profile from disk.

    Tries the runtime profile first, then falls back to the template.
    Returns a blank ``UserProfile`` if neither file is readable.
    """
    for path in (_RUNTIME_PROFILE_PATH, _TEMPLATE_PROFILE_PATH):
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return UserProfile(**data)
            except Exception:
                continue
    return UserProfile()


def save_profile(profile: UserProfile) -> None:
    """Persist the given profile to the runtime path."""
    _RUNTIME_PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _RUNTIME_PROFILE_PATH.write_text(
        profile.model_dump_json(indent=2),
        encoding="utf-8",
    )


def is_blocked_auto_fill(field_name: str) -> bool:
    """Return ``True`` if *field_name* refers to a sensitive field that must not be auto-filled."""
    return field_name.lower() in _BLOCKED_AUTO_FILL_FIELDS
