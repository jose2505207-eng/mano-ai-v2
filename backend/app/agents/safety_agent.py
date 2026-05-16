import logging

from app.schemas.web_task import ActionDecision, BrowserSnapshot, RiskLevel
from app.safety.risk import classify_risk

logger = logging.getLogger(__name__)


def assess_risk(
    decision: ActionDecision, snapshot: BrowserSnapshot | None = None
) -> RiskLevel:
    """Assess the risk level of a proposed action.

    Thin wrapper around the rule-based :func:`classify_risk` that also logs
    the result for observability.
    """
    risk = classify_risk(decision, snapshot)
    logger.info(
        f"Risk assessment for {decision.kind}: {risk} "
        f"(confidence: {decision.confidence})"
    )
    return risk
