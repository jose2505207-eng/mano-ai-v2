"""Priority-based LLM router with sponsor fallback chain.

Routing order: OpenAI → TokenRouter → Qwen Cloud → Z.ai → deterministic fallback.
Each attempt produces a SponsorLog entry for observability.
"""

import json
import re
from datetime import datetime, timezone
from typing import Any

from openai import AsyncOpenAI

from ..core.config import settings
from ..schemas.web_task import SponsorLog
from .prompts import REPAIR_JSON_SYSTEM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_log(provider: str, action: str, status: str, details: str | None = None) -> SponsorLog:
    return SponsorLog(
        provider=provider,
        action=action,
        status=status,  # type: ignore[arg-type]
        details=details,
        timestamp=_now_iso(),
    )


def _deterministic_fallback_response() -> str:
    """Return a JSON string representing a stuck action when no LLM is available."""
    return json.dumps({
        "kind": "stuck",
        "reason": "No LLM provider configured. Cannot plan next action.",
        "confidence": 0.0,
        "risk": "safe",
        "user_visible_message": "I need an LLM API key to plan actions. Please configure OPENAI_API_KEY.",
    })


def _extract_json(text: str) -> str:
    """Try to pull a JSON object out of raw LLM output (may be wrapped in markdown fences)."""
    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    return match.group() if match else cleaned


# ---------------------------------------------------------------------------
# Provider call helpers
# ---------------------------------------------------------------------------

async def _call_openai(system_prompt: str, user_message: str, model: str | None = None) -> tuple[str, SponsorLog]:
    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.chat.completions.create(
            model=model or settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
        )
        text = resp.choices[0].message.content or ""
        log = _make_log("OpenAI", "llm_call", "connected", f"model={model or settings.openai_model}")
        return text, log
    except Exception as exc:
        log = _make_log("OpenAI", "llm_call", "error", str(exc))
        return "", log


async def _call_tokenrouter(system_prompt: str, user_message: str) -> tuple[str, SponsorLog]:
    try:
        client = AsyncOpenAI(
            api_key=settings.tokenrouter_api_key,
            base_url="https://api.tokenrouter.ai/v1",
        )
        resp = await client.chat.completions.create(
            model="auto",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
        )
        text = resp.choices[0].message.content or ""
        log = _make_log("TokenRouter", "llm_call", "connected", "TokenRouter call succeeded")
        return text, log
    except Exception as exc:
        log = _make_log("TokenRouter", "llm_call", "error", str(exc))
        return "", log


async def _call_qwen(system_prompt: str, user_message: str) -> tuple[str, SponsorLog]:
    try:
        client = AsyncOpenAI(
            api_key=settings.qwen_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        resp = await client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
        )
        text = resp.choices[0].message.content or ""
        log = _make_log("Qwen Cloud", "llm_call", "connected", "Qwen Cloud call succeeded")
        return text, log
    except Exception as exc:
        log = _make_log("Qwen Cloud", "llm_call", "error", str(exc))
        return "", log


async def _call_zai(system_prompt: str, user_message: str) -> tuple[str, SponsorLog]:
    try:
        client = AsyncOpenAI(
            api_key=settings.zai_api_key,
            base_url="https://api.z.ai/v1",
        )
        resp = await client.chat.completions.create(
            model="z-pro",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
        )
        text = resp.choices[0].message.content or ""
        log = _make_log("Z.ai", "llm_call", "connected", "Z.ai call succeeded")
        return text, log
    except Exception as exc:
        log = _make_log("Z.ai", "llm_call", "error", str(exc))
        return "", log


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def llm_decide(system_prompt: str, user_message: str, model: str | None = None) -> str:
    """Route an LLM completion request through the sponsor priority chain.

    Returns the raw string response from the first successful provider, or
    a deterministic fallback JSON string if all providers fail.
    """
    # 1. OpenAI (primary)
    if settings.openai_api_key:
        text, log = await _call_openai(system_prompt, user_message, model)
        if text:
            return text

    # 2. TokenRouter
    if settings.tokenrouter_api_key:
        text, log = await _call_tokenrouter(system_prompt, user_message)
        if text:
            return text

    # 3. Qwen Cloud
    if settings.qwen_api_key:
        text, log = await _call_qwen(system_prompt, user_message)
        if text:
            return text

    # 4. Z.ai
    if settings.zai_api_key:
        text, log = await _call_zai(system_prompt, user_message)
        if text:
            return text

    # 5. Deterministic fallback
    return _deterministic_fallback_response()


async def llm_decide_json(system_prompt: str, user_message: str) -> dict[str, Any]:
    """Call :func:`llm_decide` and parse the response as JSON.

    On parse failure, retries **once** with a repair prompt. If repair also
    fails, returns ``{"kind": "stuck"}`` as a last resort.
    """
    raw = await llm_decide(system_prompt, user_message)
    extracted = _extract_json(raw)

    try:
        return json.loads(extracted)
    except json.JSONDecodeError:
        pass

    # Retry once with a repair prompt
    repair_prompt = (
        f"{REPAIR_JSON_SYSTEM}\n\n"
        f"The malformed JSON:\n{raw}"
    )
    repaired_raw = await llm_decide(repair_prompt, "Fix the JSON above.")
    repaired_extracted = _extract_json(repaired_raw)

    try:
        return json.loads(repaired_extracted)
    except json.JSONDecodeError:
        return {"kind": "stuck"}


# Module-level convenience instance (mirrors the reference code pattern)
class LLMRouter:
    """Thin wrapper kept for backward-compatibility with code that imports ``llm_router``."""

    async def complete(
        self,
        system: str,
        user: str,
        expect_json: bool = True,
    ) -> tuple[str, SponsorLog]:
        """Compatibility shim — delegates to the functional API."""
        text = await llm_decide(system, user)
        log = _make_log("router", "complete", "connected", "delegated to llm_decide")
        return text, log

    @staticmethod
    def parse_action_decision(text: str) -> dict[str, Any] | None:
        """Extract and parse an ActionDecision JSON blob from raw LLM text."""
        try:
            return json.loads(_extract_json(text))
        except Exception:
            return None


llm_router = LLMRouter()
