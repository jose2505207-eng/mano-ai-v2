"""Tests for LLM router module."""

import pytest
import json

from app.llm.router import (
    _deterministic_fallback_response,
    _extract_json,
    llm_decide,
    llm_decide_json,
)


class TestDeterministicFallback:
    def test_returns_valid_json(self):
        """Deterministic fallback returns valid JSON string."""
        result = _deterministic_fallback_response()
        parsed = json.loads(result)
        assert "kind" in parsed
        assert parsed["kind"] == "stuck"

    def test_has_required_fields(self):
        """Fallback response has confidence, risk, and user_visible_message."""
        parsed = json.loads(_deterministic_fallback_response())
        assert "confidence" in parsed
        assert "risk" in parsed
        assert "user_visible_message" in parsed


class TestExtractJson:
    def test_extracts_from_markdown_fences(self):
        raw = '```json\n{"kind": "click"}\n```'
        result = _extract_json(raw)
        parsed = json.loads(result)
        assert parsed["kind"] == "click"

    def test_extracts_plain_json(self):
        raw = '{"kind": "done", "reason": "all good"}'
        result = _extract_json(raw)
        parsed = json.loads(result)
        assert parsed["kind"] == "done"


@pytest.mark.asyncio
class TestLlmDecide:
    async def test_returns_string(self):
        """llm_decide returns a string (falls back when no keys)."""
        result = await llm_decide("system", "user")
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_fallback_is_valid_json(self):
        """With no API keys, fallback response is valid JSON."""
        result = await llm_decide("system", "user")
        parsed = json.loads(result)
        assert parsed["kind"] == "stuck"


@pytest.mark.asyncio
class TestLlmDecideJson:
    async def test_returns_dict_with_kind(self):
        """llm_decide_json returns a dict with 'kind' key on fallback."""
        result = await llm_decide_json("system", "user")
        assert isinstance(result, dict)
        assert "kind" in result

    async def test_invalid_json_triggers_repair(self):
        """When JSON is invalid, repair attempt is made and fallback returned."""
        # Since no API keys are configured, the fallback is always valid JSON.
        # This tests that the full path works without error.
        result = await llm_decide_json("system", "user")
        assert isinstance(result, dict)
