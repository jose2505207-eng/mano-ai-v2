"""Risk classification for proposed browser actions.

Classifies every ActionDecision into one of four risk levels:
  - "safe"       — can proceed automatically
  - "caution"    — proceed but log a warning
  - "sensitive"  — requires explicit user approval
  - "blocked"    — must never execute automatically
"""

import logging
from urllib.parse import urlparse

from app.schemas.web_task import ActionDecision, BrowserSnapshot, RiskLevel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain lists
# ---------------------------------------------------------------------------

SENSITIVE_DOMAINS: list[str] = [
    "dmv.ca.gov", "ssa.gov", "irs.gov", "uscis.gov",
    "medicare.gov", "healthcare.gov", "courts.gov",
    "login.gov", "id.me",
]

BLOCKED_DOMAINS: list[str] = [
    "bank", "chase.com", "wellsfargo.com", "bankofamerica.com",
    "paypal.com", "venmo.com", "zelle",
]

# ---------------------------------------------------------------------------
# Field / keyword lists
# ---------------------------------------------------------------------------

PII_FIELDS: list[str] = [
    "ssn", "social_security", "driver_license", "passport",
    "credit_card", "card_number", "cvv", "routing_number",
    "account_number", "password", "pin",
]

PAYMENT_KEYWORDS: list[str] = [
    "pay", "purchase", "buy", "checkout", "billing",
    "credit card", "debit card", "payment",
]

SUBMIT_KEYWORDS: list[str] = [
    "submit", "confirm", "finalize", "complete",
    "send", "file", "sign",
]

# ---------------------------------------------------------------------------
# Helper: domain matching
# ---------------------------------------------------------------------------

def _domain_is_blocked(url: str) -> bool:
    """Return *True* if *url* points to a blocked domain."""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return any(blocked in host for blocked in BLOCKED_DOMAINS)


def _domain_is_sensitive(url: str) -> bool:
    """Return *True* if *url* points to a sensitive domain."""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return any(host == sd or host.endswith("." + sd) for sd in SENSITIVE_DOMAINS)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_risk(
    decision: ActionDecision,
    snapshot: BrowserSnapshot | None = None,
) -> RiskLevel:
    """Classify the risk level of a proposed action.

    Rules (evaluated in order — first match wins):
    1. ``done``, ``stuck``, ``ask_user`` are always **safe**.
    2. ``request_approval`` is always **sensitive**.
    3. Navigation to a blocked domain is **blocked**.
    4. Navigation to a sensitive domain is **sensitive**.
    5. Filling a PII field is **sensitive**.
    6. Clicking a submit / payment button is **sensitive**.
    7. Clicking a payment-related element is **caution**.
    8. Everything else defaults to **safe**.
    """

    # Rule 1 — terminal safe kinds
    if decision.kind in ("done", "stuck", "ask_user"):
        logger.debug("Risk=safe for terminal kind '%s'", decision.kind)
        return "safe"

    # Rule 2 — request_approval is always sensitive
    if decision.kind == "request_approval":
        logger.debug("Risk=sensitive for request_approval")
        return "sensitive"

    # Rule 3 & 4 — domain-based risk (navigate or any action with a URL)
    target_url = _get_target_url(decision, snapshot)
    if target_url:
        if _domain_is_blocked(target_url):
            logger.warning("Risk=blocked — blocked domain: %s", target_url)
            return "blocked"
        if _domain_is_sensitive(target_url):
            logger.info("Risk=sensitive — sensitive domain: %s", target_url)
            return "sensitive"

    # Rule 5 — filling a PII field
    if decision.kind == "fill" and snapshot:
        element = _find_element(snapshot, decision.ref)
        if element and is_pii_field(element.name, element.placeholder, element.input_type):
            logger.info("Risk=sensitive — PII field fill: ref=%s", decision.ref)
            return "sensitive"
    # Also check the decision value for PII-like content even without snapshot
    if decision.kind == "fill" and _value_looks_like_pii(decision.value or ""):
        logger.info("Risk=sensitive — PII-like value in fill action")
        return "sensitive"

    # Rule 6 — clicking submit / payment buttons
    if decision.kind == "click" and snapshot:
        element = _find_element(snapshot, decision.ref)
        if element:
            el_text = (element.text or "").lower()
            el_name = (element.name or "").lower()
            combined = f"{el_text} {el_name}"
            if any(kw in combined for kw in SUBMIT_KEYWORDS):
                logger.info("Risk=sensitive — submit button click: ref=%s", decision.ref)
                return "sensitive"
            if any(kw in combined for kw in PAYMENT_KEYWORDS):
                logger.info("Risk=sensitive — payment button click: ref=%s", decision.ref)
                return "sensitive"

    # Rule 7 — broader payment caution
    if is_payment_action(decision, snapshot):
        logger.info("Risk=caution — payment-related action")
        return "caution"

    # Rule 8 — default safe
    logger.debug("Risk=safe (default) for kind='%s'", decision.kind)
    return "safe"


def is_pii_field(
    element_name: str | None,
    element_placeholder: str | None,
    element_type: str | None,
) -> bool:
    """Return *True* if a form field likely collects Personally Identifiable Information.

    Checks the element's ``name``, ``placeholder``, and ``input_type`` against
    the known PII field list.  All comparisons are case-insensitive.
    """
    fields_to_check = [
        (element_name or "").lower(),
        (element_placeholder or "").lower(),
        (element_type or "").lower(),
    ]
    combined = " ".join(fields_to_check)
    return any(pii in combined for pii in PII_FIELDS)


def is_payment_action(
    decision: ActionDecision,
    snapshot: BrowserSnapshot | None = None,
) -> bool:
    """Return *True* if an action involves payment.

    Checks the decision's ``reason``, ``value``, and the text of the
    referenced element for payment-related keywords.
    """
    texts = [(decision.reason or "").lower(), (decision.value or "").lower()]
    if snapshot and decision.ref:
        element = _find_element(snapshot, decision.ref)
        if element:
            texts.append((element.text or "").lower())
            texts.append((element.name or "").lower())
    combined = " ".join(texts)
    return any(kw in combined for kw in PAYMENT_KEYWORDS)


# Search engine domains where form submission is always safe (no approval needed)
SEARCH_ENGINE_DOMAINS = [
    "google.com/flights", "google.com/travel",
    "kayak.com", "skyscanner.com", "expedia.com",
    "booking.com", "airbnb.com", "tripadvisor.com",
    "google.com/search", "bing.com", "duckduckgo.com",
]


def is_submit_action(
    decision: ActionDecision,
    snapshot: BrowserSnapshot | None = None,
) -> bool:
    """Return *True* if an action is a form submission.

    Checks the decision's ``reason`` and the text of the referenced element
    for submit-related keywords.  Exempts search engine pages where clicking
    a search/submit button is always safe.
    """
    # Exemption: on search engines, clicking submit/search is always safe
    if snapshot and snapshot.url:
        page_url = snapshot.url.lower()
        if any(domain in page_url for domain in SEARCH_ENGINE_DOMAINS):
            return False

    texts = [(decision.reason or "").lower()]
    if snapshot and decision.ref:
        element = _find_element(snapshot, decision.ref)
        if element:
            texts.append((element.text or "").lower())
            texts.append((element.name or "").lower())
    combined = " ".join(texts)
    return any(kw in combined for kw in SUBMIT_KEYWORDS)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_target_url(decision: ActionDecision, snapshot: BrowserSnapshot | None) -> str | None:
    """Extract the target URL from a decision (navigate action or current page)."""
    if decision.kind == "navigate":
        return decision.url or decision.value
    # For non-navigate actions, check the current page URL
    if snapshot and snapshot.url:
        return snapshot.url
    return None


def _find_element(snapshot: BrowserSnapshot, ref: str | None) -> "BrowserElement | None":
    """Find an element in the snapshot by its ref identifier."""
    if not ref:
        return None
    return next((el for el in snapshot.elements if el.ref == ref), None)


def _value_looks_like_pii(value: str) -> bool:
    """Heuristic check whether a fill value resembles PII (e.g. SSN pattern)."""
    import re
    v = value.lower().strip()
    # SSN pattern: XXX-XX-XXXX or XXX XX XXXX
    if re.match(r"^\d{3}[-\s]\d{2}[-\s]\d{4}$", v):
        return True
    # Credit card pattern: 4 groups of 4 digits
    if re.match(r"^\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}$", v):
        return True
    return False
