import logging

from app.schemas.web_task import BrowserSnapshot, BrowserElement, UserProfile

logger = logging.getLogger(__name__)

# Mapping of common field indicators to profile attributes
FIELD_MAP: dict[str, str] = {
    "name": "full_name",
    "full_name": "full_name",
    "first_name": "full_name",   # will need splitting
    "last_name": "full_name",    # will need splitting
    "email": "email",
    "phone": "phone",
    "telephone": "phone",
    "tel": "phone",
    "dob": "date_of_birth",
    "date_of_birth": "date_of_birth",
    "birthday": "date_of_birth",
    "birth_date": "date_of_birth",
    "address": "address",
    "street": "address",
}


def extract_form_fields(snapshot: BrowserSnapshot) -> list[BrowserElement]:
    """Extract all fillable form fields from a snapshot."""
    return [
        el
        for el in snapshot.elements
        if (
            el.tag in ("input", "textarea", "select")
            or el.role in ("INPUT", "SELECT")
        )
        and el.visible
    ]


def match_field_to_profile(
    element: BrowserElement, profile: UserProfile
) -> str | None:
    """Try to match a form field to a profile value.

    Returns the value to fill, or ``None`` if no match is found.
    """
    indicators = [
        (element.name or "").lower(),
        (element.placeholder or "").lower(),
        (element.input_type or "").lower(),
    ]

    for indicator in indicators:
        for keyword, attr in FIELD_MAP.items():
            if keyword in indicator:
                value = getattr(profile, attr, None)
                if not value:
                    continue

                # Format DOB as MM/DD/YYYY
                if attr == "date_of_birth" and "-" in value:
                    parts = value.split("-")
                    if len(parts) == 3:
                        return f"{parts[1]}/{parts[2]}/{parts[0]}"

                # Handle first / last name splitting
                if "first" in indicator and attr == "full_name":
                    return value.split()[0] if value else None
                if "last" in indicator and attr == "full_name":
                    parts = value.split()
                    return parts[-1] if len(parts) > 1 else None

                return value
    return None


def get_form_fill_plan(
    snapshot: BrowserSnapshot, profile: UserProfile
) -> list[dict]:
    """Generate a plan of fields to fill automatically from profile.

    Returns:
        list of ``{"ref": str, "value": str, "field_name": str}``
    """
    plan: list[dict] = []
    for field in extract_form_fields(snapshot):
        value = match_field_to_profile(field, profile)
        if value:
            plan.append(
                {
                    "ref": field.ref,
                    "value": value,
                    "field_name": field.name or field.placeholder or "unknown",
                }
            )
    return plan
