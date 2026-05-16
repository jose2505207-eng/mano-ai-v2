"""Tests for safety module: risk classification and action validation."""

import pytest

from app.schemas.web_task import ActionDecision, BrowserElement, BrowserSnapshot, WebTaskStep, ActionResult
from app.safety.risk import classify_risk, is_pii_field, is_payment_action
from app.safety.validator import validate_action, ValidationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_decision(kind="click", ref=None, url=None, value=None,
                   reason="test", confidence=0.8, risk="safe"):
    return ActionDecision(
        kind=kind, ref=ref, url=url, value=value,
        reason=reason, confidence=confidence, risk=risk,
        user_visible_message="testing",
    )


def _make_snapshot(url="https://example.com", elements=None):
    return BrowserSnapshot(
        url=url,
        text_summary="Test page",
        elements=elements or [],
    )


def _make_step(kind="click", ref=None):
    decision = _make_decision(kind=kind, ref=ref)
    return WebTaskStep(step_number=1, decision=decision)


# ---------------------------------------------------------------------------
# classify_risk tests
# ---------------------------------------------------------------------------

class TestClassifyRisk:
    def test_safe_actions(self):
        """scroll, wait, extract are safe."""
        for kind in ("scroll", "wait", "extract"):
            d = _make_decision(kind=kind)
            assert classify_risk(d) == "safe"

    def test_terminal_safe_actions(self):
        """ask_user, done, stuck are safe."""
        for kind in ("ask_user", "done", "stuck"):
            d = _make_decision(kind=kind)
            assert classify_risk(d) == "safe"

    def test_request_approval_is_sensitive(self):
        d = _make_decision(kind="request_approval")
        assert classify_risk(d) == "sensitive"

    def test_blocked_domains(self):
        """Navigation to blocked domains returns 'blocked'."""
        for domain in ("chase.com", "paypal.com"):
            d = _make_decision(kind="navigate", url=f"https://{domain}/login")
            assert classify_risk(d) == "blocked"

    def test_sensitive_domains(self):
        """Navigation to sensitive government domains returns 'sensitive'."""
        for domain in ("dmv.ca.gov", "ssa.gov"):
            d = _make_decision(kind="navigate", url=f"https://{domain}/")
            assert classify_risk(d) == "sensitive"


# ---------------------------------------------------------------------------
# is_pii_field tests
# ---------------------------------------------------------------------------

class TestIsPiiField:
    def test_detects_ssn(self):
        assert is_pii_field("ssn", None, None) is True

    def test_detects_credit_card(self):
        assert is_pii_field("credit_card", None, None) is True

    def test_detects_password_in_placeholder(self):
        assert is_pii_field(None, "Enter your password", None) is True

    def test_normal_field_not_pii(self):
        assert is_pii_field("email", "Enter email", "email") is False


# ---------------------------------------------------------------------------
# is_payment_action tests
# ---------------------------------------------------------------------------

class TestIsPaymentAction:
    def test_detects_payment_in_reason(self):
        d = _make_decision(kind="click", reason="proceed to checkout")
        assert is_payment_action(d) is True

    def test_normal_action_not_payment(self):
        d = _make_decision(kind="click", reason="navigate to results")
        assert is_payment_action(d) is False


# ---------------------------------------------------------------------------
# validate_action tests
# ---------------------------------------------------------------------------

class TestValidateAction:
    def test_nonexistent_element_ref(self):
        """Action referencing a non-existent element is invalid."""
        elements = [BrowserElement(ref="btn1")]
        snapshot = _make_snapshot(elements=elements)
        d = _make_decision(kind="click", ref="btn999")
        result = validate_action(d, snapshot)
        assert result.valid is False
        assert "not found" in result.reason

    def test_url_loop_detection(self):
        """Navigating to the current URL is blocked."""
        snapshot = _make_snapshot(url="https://example.com/page")
        d = _make_decision(kind="navigate", url="https://example.com/page")
        result = validate_action(d, snapshot)
        assert result.valid is False
        assert "loop" in result.reason.lower()

    def test_action_loop_detection(self):
        """Same action repeated 3+ times in last 5 steps is blocked."""
        history = [_make_step(kind="click", ref="btn1") for _ in range(3)]
        snapshot = _make_snapshot(elements=[BrowserElement(ref="btn1")])
        d = _make_decision(kind="click", ref="btn1")
        result = validate_action(d, snapshot, history=history)
        assert result.valid is False
        assert "loop" in result.reason.lower()

    def test_pii_field_requires_approval(self):
        """Filling a PII field requires approval."""
        elements = [BrowserElement(ref="ssn_input", name="ssn", input_type="text")]
        snapshot = _make_snapshot(elements=elements)
        d = _make_decision(kind="fill", ref="ssn_input", value="123-45-6789")
        result = validate_action(d, snapshot)
        assert result.valid is True
        assert result.requires_approval is True

    def test_payment_action_requires_approval(self):
        """Payment actions require approval."""
        d = _make_decision(kind="click", reason="proceed to payment checkout")
        result = validate_action(d, None)
        assert result.valid is True
        assert result.requires_approval is True
