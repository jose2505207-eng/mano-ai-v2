"""Action validator — the last line of defense before browser execution.

Every proposed ActionDecision passes through :func:`validate_action` which
applies a series of deterministic checks.  The validator never makes LLM
calls and never performs async I/O — it is purely rule-based.
"""

import logging
from urllib.parse import urlparse

from app.schemas.web_task import ActionDecision, BrowserSnapshot, WebTaskStep
from app.core.config import settings
from .risk import classify_risk, is_pii_field, is_payment_action, is_submit_action

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

class ValidationResult:
    """Outcome of validating a single proposed action.

    Attributes:
        valid: Whether the action may proceed at all.
        reason: Human-readable explanation when *valid* is ``False``.
        requires_approval: Whether the action needs explicit user approval
            before execution (even though it is technically valid).
        approval_reason: Human-readable explanation of *why* approval is
            required.
    """

    def __init__(
        self,
        valid: bool,
        reason: str = "",
        requires_approval: bool = False,
        approval_reason: str = "",
    ) -> None:
        self.valid = valid
        self.reason = reason
        self.requires_approval = requires_approval
        self.approval_reason = approval_reason

    def __repr__(self) -> str:
        parts = [f"valid={self.valid}"]
        if self.reason:
            parts.append(f"reason='{self.reason}'")
        if self.requires_approval:
            parts.append(f"requires_approval=True")
            parts.append(f"approval_reason='{self.approval_reason}'")
        return f"ValidationResult({', '.join(parts)})"


# ---------------------------------------------------------------------------
# URL normalisation helper
# ---------------------------------------------------------------------------

def _normalize_url(url: str) -> str:
    """Normalize a URL for comparison.

    Strips the fragment identifier, removes trailing slashes, and
    lower-cases the host.  Query parameters are preserved because
    ``?page=1`` and ``?page=2`` are genuinely different pages.
    """
    parsed = urlparse(url)
    # Rebuild without fragment, strip trailing slash from path
    path = parsed.path.rstrip("/")
    return parsed._replace(fragment="", path=path).geturl().lower()


# ---------------------------------------------------------------------------
# Main validation entry point
# ---------------------------------------------------------------------------

def validate_action(
    decision: ActionDecision,
    snapshot: BrowserSnapshot | None,
    history: list[WebTaskStep] | None = None,
) -> ValidationResult:
    """Validate a proposed action before execution.

    Checks (evaluated in order):

    1. **Element ref exists** — the referenced element must be present in
       the current snapshot.
    2. **URL loop detection** — navigating to the current URL is blocked.
    3. **Action loop detection** — same ``kind + ref`` repeated 3+ times
       in the last 5 steps.
    4. **Mid-flow navigation prevention** — navigating away during an
       active form-filling sequence requires high confidence.
    5. **PII approval gate** — filling a sensitive field requires approval
       when ``settings.require_approval_for_pii`` is ``True``.
    6. **Payment approval gate** — payment actions require approval when
       ``settings.require_approval_for_payment`` is ``True``.
    7. **Submit approval gate** — form submissions require approval when
       ``settings.require_approval_for_submit`` is ``True``.
    8. **Risk classification override** — if the classified risk is higher
       than the decision's stated risk, the action is blocked or upgraded.

    Returns:
        :class:`ValidationResult` indicating whether the action can
        proceed, whether it requires approval, and why.
    """

    history = history or []

    # ------------------------------------------------------------------
    # 1. Element ref must exist in the snapshot
    # ------------------------------------------------------------------
    if decision.ref and snapshot:
        refs = {el.ref for el in snapshot.elements}
        if decision.ref not in refs:
            sample_refs = sorted(refs)[:10]
            msg = (
                f"Element ref '{decision.ref}' not found in current snapshot. "
                f"Available refs: {sample_refs}"
            )
            logger.warning("Validation blocked: %s", msg)
            return ValidationResult(valid=False, reason=msg)

    # ------------------------------------------------------------------
    # 2. URL loop detection
    # ------------------------------------------------------------------
    if decision.kind == "navigate" and snapshot:
        target_url = decision.url or decision.value
        if target_url and snapshot.url:
            try:
                current = _normalize_url(snapshot.url)
                target = _normalize_url(target_url)
                if current == target:
                    msg = f"URL loop detected: already on {snapshot.url}"
                    logger.warning("Validation blocked: %s", msg)
                    return ValidationResult(valid=False, reason=msg)
            except Exception:
                # If URL parsing fails, don't block — let it through
                logger.debug("URL normalisation failed, skipping loop check")

    # ------------------------------------------------------------------
    # 3. Action loop detection (same kind+ref 3+ times in last 5 steps)
    # ------------------------------------------------------------------
    if history and len(history) >= 3:
        recent = history[-5:]
        same_action_count = sum(
            1
            for step in recent
            if step.decision.kind == decision.kind
            and step.decision.ref == decision.ref
        )
        if same_action_count >= 3:
            msg = (
                f"Action loop detected: {decision.kind} on {decision.ref} "
                f"repeated {same_action_count} times in last 5 steps"
            )
            logger.warning("Validation blocked: %s", msg)
            return ValidationResult(valid=False, reason=msg)

    # ------------------------------------------------------------------
    # 4. Mid-flow navigation prevention
    # ------------------------------------------------------------------
    if decision.kind == "navigate" and history:
        recent_kinds = [s.decision.kind for s in history[-3:]]
        if "fill" in recent_kinds or "select" in recent_kinds:
            # In a form flow — navigation might lose progress
            if decision.confidence < 0.9:
                msg = (
                    "Mid-flow navigation blocked: recent form interactions "
                    "detected. High confidence required."
                )
                logger.warning("Validation blocked: %s", msg)
                return ValidationResult(valid=False, reason=msg)

    # ------------------------------------------------------------------
    # 5. PII approval gate
    # ------------------------------------------------------------------
    if decision.kind == "fill" and settings.require_approval_for_pii:
        if snapshot:
            element = next(
                (el for el in snapshot.elements if el.ref == decision.ref),
                None,
            )
            if element and is_pii_field(
                element.name, element.placeholder, element.input_type
            ):
                field_label = element.name or element.placeholder or "PII field"
                msg = f"Filling sensitive field: {field_label}"
                logger.info("Approval required: %s", msg)
                return ValidationResult(
                    valid=True,
                    requires_approval=True,
                    approval_reason=msg,
                )

    # ------------------------------------------------------------------
    # 6. Payment approval gate
    # ------------------------------------------------------------------
    if settings.require_approval_for_payment and is_payment_action(decision, snapshot):
        msg = "Payment action detected — requires user approval"
        logger.info("Approval required: %s", msg)
        return ValidationResult(
            valid=True,
            requires_approval=True,
            approval_reason=msg,
        )

    # ------------------------------------------------------------------
    # 7. Submit approval gate
    # ------------------------------------------------------------------
    if settings.require_approval_for_submit and is_submit_action(decision, snapshot):
        msg = "Form submission detected — requires user approval"
        logger.info("Approval required: %s", msg)
        return ValidationResult(
            valid=True,
            requires_approval=True,
            approval_reason=msg,
        )

    # ------------------------------------------------------------------
    # 8. Risk classification override
    # ------------------------------------------------------------------
    actual_risk = classify_risk(decision, snapshot)

    if actual_risk == "blocked":
        msg = (
            "Action blocked: domain or action type is not allowed "
            "for automated execution"
        )
        logger.warning("Validation blocked by risk classification: %s", msg)
        return ValidationResult(valid=False, reason=msg)

    if actual_risk == "sensitive" and decision.risk in ("safe", "caution"):
        msg = (
            f"Risk upgraded to 'sensitive' (was '{decision.risk}'): "
            f"{decision.reason}"
        )
        logger.info("Risk upgrade: %s", msg)
        return ValidationResult(
            valid=True,
            requires_approval=True,
            approval_reason=msg,
        )

    # ------------------------------------------------------------------
    # All checks passed
    # ------------------------------------------------------------------
    logger.debug(
        "Action validated: kind='%s' ref='%s' risk='%s'",
        decision.kind,
        decision.ref,
        decision.risk,
    )
    return ValidationResult(valid=True)
