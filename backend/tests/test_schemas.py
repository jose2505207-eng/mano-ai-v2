"""Tests for Pydantic schema models."""

import pytest
from pydantic import ValidationError

from app.schemas.web_task import (
    ActionDecision,
    ActionResult,
    BrowserElement,
    BrowserSnapshot,
    SponsorLog,
    TaskConstraints,
    UserProfile,
    WebTaskRun,
    WebTaskStep,
)


class TestUserProfile:
    def test_defaults(self):
        p = UserProfile()
        assert p.full_name is None
        assert p.preferred_language == "en"
        assert p.payment_allowed is False

    def test_full_data(self):
        p = UserProfile(
            full_name="Jose Ivan Zaragoza",
            email="jose@example.com",
            phone="408-555-0100",
            date_of_birth="2004-06-11",
            address="123 Main St, San Jose, CA",
            preferred_language="es",
            preferred_airport="SFO",
            payment_allowed=True,
        )
        assert p.full_name == "Jose Ivan Zaragoza"
        assert p.preferred_language == "es"
        assert p.payment_allowed is True

    def test_edge_case_empty_strings(self):
        p = UserProfile(full_name="", email="")
        assert p.full_name == ""


class TestTaskConstraints:
    def test_defaults(self):
        tc = TaskConstraints()
        assert tc.budget is None
        assert tc.must_ask_before_submit is True
        assert tc.allow_account_creation is False


class TestBrowserElement:
    def test_creation(self):
        el = BrowserElement(ref="btn1", role="button", tag="button", text="Click me")
        assert el.ref == "btn1"
        assert el.visible is True


class TestBrowserSnapshot:
    def test_creation(self):
        snap = BrowserSnapshot(url="https://example.com", text_summary="Example page")
        assert snap.url == "https://example.com"
        assert snap.elements == []


class TestActionDecision:
    @pytest.mark.parametrize("kind", [
        "navigate", "search_web", "click", "fill", "select",
        "scroll", "wait", "extract", "ask_user",
        "request_approval", "done", "stuck",
    ])
    def test_valid_kinds(self, kind):
        ad = ActionDecision(
            kind=kind,
            reason="test",
            confidence=0.5,
            risk="safe",
            user_visible_message="testing",
        )
        assert ad.kind == kind

    def test_confidence_too_high(self):
        with pytest.raises(ValidationError):
            ActionDecision(
                kind="click",
                reason="test",
                confidence=1.5,
                risk="safe",
                user_visible_message="testing",
            )

    def test_invalid_risk_level(self):
        with pytest.raises(ValidationError):
            ActionDecision(
                kind="click",
                reason="test",
                confidence=0.5,
                risk="invalid_level",
                user_visible_message="testing",
            )


class TestActionResult:
    def test_creation(self):
        ar = ActionResult(success=True, message="done")
        assert ar.success is True
        assert ar.screenshot is None


class TestWebTaskStep:
    def test_creation(self):
        decision = ActionDecision(
            kind="click", reason="test", confidence=0.8,
            risk="safe", user_visible_message="clicking",
        )
        step = WebTaskStep(step_number=1, decision=decision)
        assert step.step_number == 1
        assert step.result is None
        assert step.sponsor_logs == []


class TestWebTaskRun:
    @pytest.mark.parametrize("status", [
        "running", "waiting_for_user", "waiting_for_approval",
        "done", "stuck", "failed",
    ])
    def test_valid_statuses(self, status):
        run = WebTaskRun(task_id="t1", task="test task", status=status)
        assert run.status == status


class TestSponsorLog:
    def test_creation(self):
        sl = SponsorLog(
            provider="OpenAI",
            action="llm_call",
            status="connected",
            details="model=gpt-4o-mini",
            timestamp="2024-01-01T00:00:00Z",
        )
        assert sl.provider == "OpenAI"
        assert sl.status == "connected"
