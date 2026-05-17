"""Core orchestration engine for Mano AI web tasks.

Flow:
1. Parse intent from user task
2. Find starting URL
3. Launch browser
4. Loop:
   a. Observe browser state (snapshot)
   b. Ask LLM for next action decision
   c. Validate action (safety checks)
   d. If requires approval → pause, set status to waiting_for_approval
   e. If needs user input → pause, set status to waiting_for_user
   f. Execute action on browser
   g. Record step
   h. Check if done/stuck
   i. Repeat until done, stuck, failed, or max steps
5. Summarize results
"""

import asyncio
import logging
import uuid

from app.schemas.web_task import (
    WebTaskRun,
    WebTaskStep,
    ActionDecision,
    ActionResult,
    BrowserSnapshot,
    UserProfile,
)
from app.core.config import settings
from app.llm.router import llm_decide_json
from app.llm.prompts import BROWSER_DECISION_SYSTEM
from app.safety.validator import validate_action

from .intent_agent import parse_intent
from .search_agent import find_start_url
from .browser_agent import execute_browser_action
from .safety_agent import assess_risk
from .memory_agent import get_user_profile
from .critic_agent import evaluate_decision
from .summary_agent import summarize_task

logger = logging.getLogger(__name__)


class Orchestrator:
    """Core orchestration engine for Mano AI web tasks.

    Manages the full lifecycle of a web task: intent parsing, browser
    navigation, action execution, safety gating, and result summarization.

    Supports pausing/resuming for user approval and user input.
    """

    def __init__(self) -> None:
        from app.browser.manager import BrowserManager
        self.browser_manager = BrowserManager()
        self.task_run: WebTaskRun | None = None
        self._profile: UserProfile | None = None
        self._language: str = "en"
        self._resume_event: asyncio.Event = asyncio.Event()
        self._user_input: str | None = None
        self._approved: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(
        self,
        task: str,
        language: str = "en",
        profile: UserProfile | None = None,
        constraints: dict | None = None,
    ) -> WebTaskRun:
        """Execute a complete web task."""
        task_id = str(uuid.uuid4())
        self._language = language
        self._profile = profile or get_user_profile()

        self.task_run = WebTaskRun(
            task_id=task_id,
            task=task,
            status="running",
        )

        try:
            await self._execute(task, task_id)
        except Exception as e:
            logger.error(f"[{task_id}] Orchestrator error: {e}", exc_info=True)
            self.task_run.status = "failed"
            self.task_run.final_answer = f"Task failed: {str(e)}"
        finally:
            await self.browser_manager.close()

        return self.task_run

    def resume_with_approval(self, approved: bool) -> None:
        """Resume after user approval/denial."""
        self._approved = approved
        self._resume_event.set()

    def resume_with_input(self, user_input: str) -> None:
        """Resume after user provides input."""
        self._user_input = user_input
        self._resume_event.set()

    def stop(self) -> None:
        """Stop the task immediately."""
        if self.task_run:
            self.task_run.status = "failed"
            self.task_run.final_answer = "Task stopped by user."
        self._resume_event.set()

    # ------------------------------------------------------------------
    # Main execution loop
    # ------------------------------------------------------------------

    async def _execute(self, task: str, task_id: str) -> None:
        """Run the full task pipeline (called inside :meth:`run`)."""

        # Step 1: Parse intent
        logger.info(f"[{task_id}] Parsing intent: {task}")
        intent = await parse_intent(task)
        logger.info(f"[{task_id}] Intent: {intent}")

        # Step 2: Find start URL
        start_url = await find_start_url(task, intent)
        logger.info(f"[{task_id}] Start URL: {start_url}")

        # Step 3: Launch browser
        provider = await self.browser_manager.get_provider()

        # Step 4: Navigate to start URL
        nav_result = await provider.navigate(start_url)
        # Take screenshot of initial page so the user sees something immediately
        initial_screenshot = await provider.screenshot()
        if initial_screenshot:
            nav_result.screenshot = initial_screenshot
        self.task_run.current_url = start_url
        self._add_step(
            ActionDecision(
                kind="navigate",
                url=start_url,
                reason="Starting task — navigating to initial URL",
                confidence=1.0,
                risk="safe",
                user_visible_message=f"Opening {start_url}",
            ),
            nav_result,
        )

        # Step 5: Main agent loop
        for step_num in range(settings.max_agent_steps):
            if self.task_run.status in ("done", "stuck", "failed"):
                break

            # 5a. Observe browser
            snapshot = await provider.observe()
            self.task_run.current_url = snapshot.url

            # 5b. Build context for LLM
            context = self._build_llm_context(snapshot)

            # 5c. Ask LLM for next action
            decision_dict = await llm_decide_json(BROWSER_DECISION_SYSTEM, context)
            decision = self._parse_decision(decision_dict)

            # Override risk with our own classification
            decision.risk = assess_risk(decision, snapshot)

            # 5d. Critic evaluation (every 3 steps or on sensitive actions)
            if step_num % 3 == 0 or decision.risk in ("sensitive", "blocked"):
                critic_result = await evaluate_decision(
                    decision, snapshot, task, self.task_run.steps
                )
                if not critic_result["approved"]:
                    logger.warning(
                        f"[{task_id}] Critic rejected: {critic_result['reason']}"
                    )
                    if critic_result.get("suggested_alternative"):
                        decision = self._parse_decision(
                            critic_result["suggested_alternative"]
                        )
                    else:
                        decision = ActionDecision(
                            kind="stuck",
                            reason=critic_result["reason"],
                            confidence=0.0,
                            risk="safe",
                            user_visible_message=(
                                f"I'm having trouble: {critic_result['reason']}"
                            ),
                        )

            # 5e. Validate action (safety gate)
            validation = validate_action(
                decision, snapshot, self.task_run.steps
            )

            if not validation.valid:
                logger.warning(
                    f"[{task_id}] Validation failed: {validation.reason}"
                )
                self._add_step(
                    decision,
                    ActionResult(
                        success=False,
                        message=f"Blocked: {validation.reason}",
                    ),
                )
                # Try to recover — ask LLM again with error context
                continue

            if validation.requires_approval:
                # Pause for user approval
                self.task_run.status = "waiting_for_approval"
                self.task_run.requires_approval = True
                self.task_run.approval_reason = validation.approval_reason
                self._add_step(
                    ActionDecision(
                        kind="request_approval",
                        reason=validation.approval_reason,
                        confidence=decision.confidence,
                        risk=decision.risk,
                        user_visible_message=validation.approval_reason,
                    ),
                    None,
                )

                # Wait for user response
                self._resume_event.clear()
                await self._resume_event.wait()

                if not self._approved:
                    self.task_run.status = "done"
                    self.task_run.final_answer = (
                        "Task stopped by user at approval gate."
                    )
                    break

                # User approved — continue with original decision
                self.task_run.status = "running"
                self.task_run.requires_approval = False
                self.task_run.approval_reason = None

            # 5f. Handle terminal actions
            if decision.kind == "done":
                self.task_run.status = "done"
                if decision.user_visible_message:
                    self.task_run.final_answer = decision.user_visible_message
                self._add_step(
                    decision,
                    ActionResult(success=True, message="Task completed"),
                )
                break

            if decision.kind == "stuck":
                self.task_run.status = "stuck"
                self._add_step(
                    decision,
                    ActionResult(success=False, message="Agent is stuck"),
                )
                break

            if decision.kind == "ask_user":
                self.task_run.status = "waiting_for_user"
                self._add_step(decision, None)

                # Wait for user input
                self._resume_event.clear()
                await self._resume_event.wait()

                self.task_run.status = "running"
                # User input available in self._user_input
                continue

            # 5g. Loop detection: if same action repeated 3+ times, mark stuck
            if self._is_in_loop(decision):
                logger.warning(f"[{task_id}] Loop detected: same action repeated 3+ times")
                self.task_run.status = "stuck"
                self._add_step(
                    decision,
                    ActionResult(success=False, message="Loop detected: same action repeated 3+ times without progress"),
                )
                break

            # 5h. Execute action on browser
            result = await execute_browser_action(provider, decision)

            # Take screenshot after action
            screenshot = await provider.screenshot()
            if screenshot:
                result.screenshot = screenshot

            self._add_step(decision, result)

            if not result.success:
                logger.warning(
                    f"[{task_id}] Action failed: {result.message}"
                )
                # If ref not found or not visible, re-observe so next LLM call uses fresh refs
                if "not found" in result.message.lower() or "not visible" in result.message.lower():
                    logger.info(f"[{task_id}] Ref error detected — re-observing page")
                    snapshot = await provider.observe()
                    self.task_run.current_url = snapshot.url

            # Wait for page to stabilize after action
            await asyncio.sleep(1.5)

        else:
            # Max steps reached
            self.task_run.status = "stuck"
            logger.warning(
                f"[{task_id}] Max steps ({settings.max_agent_steps}) reached"
            )

        # Step 6: Summarize
        if self.task_run.status in ("done", "stuck"):
            self.task_run.final_answer = await summarize_task(
                task, self.task_run.steps, self._language
            )

    # ------------------------------------------------------------------
    # Loop detection
    # ------------------------------------------------------------------

    def _is_in_loop(self, decision: ActionDecision) -> bool:
        """Detect if the agent is stuck in a loop.

        Checks for:
        1. Same exact action repeated 2+ times consecutively
        2. Alternating between 2 actions 4+ times (A, B, A, B pattern)
        """
        if not self.task_run or not self.task_run.steps:
            return False

        action_key = f"{decision.kind}:{decision.ref or ''}:{decision.value or ''}"

        # Check 1: Consecutive identical actions (2+ times)
        consecutive_count = 0
        for step in reversed(self.task_run.steps):
            step_key = f"{step.decision.kind}:{step.decision.ref or ''}:{step.decision.value or ''}"
            if step_key == action_key:
                consecutive_count += 1
            else:
                break
        if consecutive_count >= 2:
            return True

        # Check 2: Alternating pattern — same 2 actions repeating 4+ times
        if len(self.task_run.steps) >= 4:
            recent_keys = [
                f"{s.decision.kind}:{s.decision.ref or ''}:{s.decision.value or ''}"
                for s in self.task_run.steps[-6:]
            ]
            # Check if we're alternating between 2 unique actions
            unique_keys = set(recent_keys)
            if len(unique_keys) == 2 and len(recent_keys) >= 4:
                # Verify it's truly alternating (A, B, A, B or B, A, B, A)
                is_alternating = True
                for i in range(len(recent_keys) - 1):
                    if recent_keys[i] == recent_keys[i + 1]:
                        is_alternating = False
                        break
                if is_alternating:
                    return True

        return False

    # ------------------------------------------------------------------
    # Context building
    # ------------------------------------------------------------------

    def _build_llm_context(self, snapshot: BrowserSnapshot) -> str:
        """Build the context string for LLM decision-making."""
        parts: list[str] = [
            f"=== USER'S TASK ===",
            f"{self.task_run.task}",
            f"=== END TASK ===",
            "",
            f"CURRENT URL: {snapshot.url}",
            f"PAGE TITLE: {snapshot.title or 'N/A'}",
            f"LANGUAGE: {self._language}",
            "",
            "RULE: If the user's task already contains dates, locations, or preferences, USE THEM directly. Do NOT ask_user for information that is already in the task description.",
            "",
            f"PAGE TEXT (first {len(snapshot.text_summary)} chars):",
            snapshot.text_summary,
            "",
            "INTERACTIVE ELEMENTS:",
        ]

        for el in snapshot.elements:
            if not el.visible:
                continue
            role_tag = f"[{el.role}]" if el.role else f"[{el.tag}]"
            text_info = el.text or el.placeholder or el.name or ""
            ref_tag = f"ref={el.ref}"
            value_info = f' value="{el.value}"' if el.value else ""
            type_info = f" type={el.input_type}" if el.input_type else ""
            # Tag date-related fields so LLM knows to use select_date
            date_hint = ""
            text_lower = text_info.lower()
            if el.role in ("GRIDCELL",) or el.input_type == "date":
                date_hint = " [DATE-FIELD: use select_date]"
            elif any(kw in text_lower for kw in ["date", "departure", "return", "check-in", "check-out", "depart", "calendar", "fecha"]):
                date_hint = " [DATE-FIELD: use select_date]"
            parts.append(
                f"  {ref_tag} {role_tag} {text_info}{type_info}{value_info}{date_hint}"
            )

        parts.append("")
        parts.append("IMPORTANT: Only use refs listed above. Previous step refs are now INVALID.")

        # Check if results are already visible on the page
        # Only do this after the agent has actually filled/clicked something (step 3+)
        has_done_form_work = (
            self.task_run is not None
            and len(self.task_run.steps) >= 3
            and any(
                s.decision.kind in ("fill", "click", "select_date", "select")
                for s in self.task_run.steps
            )
        )
        if has_done_form_work:
            page_text_lower = snapshot.text_summary.lower() if snapshot.text_summary else ""
            result_indicators = ["departing", "arriving", "nonstop", "1 stop", "2 stops",
                                 "round trip", "one way", "economy", "business class", "best flights",
                                 "best departing", "cheapest", "best price"]
            visible_results = sum(1 for ind in result_indicators if ind in page_text_lower)
            if visible_results >= 2:
                parts.append("")
                parts.append("✅ FLIGHT/SEARCH RESULTS APPEAR TO BE VISIBLE ON THIS PAGE.")
                parts.append("If you can see prices or results in the elements above, the search is DONE.")
                parts.append("Use action kind 'done' with a summary of the results you see.")

        # Add profile info for form filling
        if self._profile:
            parts.append("")
            parts.append("USER PROFILE (for form filling):")
            profile_dict = self._profile.model_dump(exclude_none=True)
            for k, v in profile_dict.items():
                if v and k != "payment_allowed":
                    parts.append(f"  {k}: {v}")

        # Add recent history
        if self.task_run and self.task_run.steps:
            parts.append("")
            parts.append("RECENT ACTIONS:")
            for step in self.task_run.steps[-5:]:
                result_msg = ""
                if step.result:
                    mark = "\u2713" if step.result.success else "\u2717"
                    result_msg = f" \u2192 {mark} {step.result.message}"
                parts.append(
                    f"  Step {step.step_number}: {step.decision.kind} "
                    f"{step.decision.ref or ''} "
                    f"{step.decision.value or ''}"
                    f"{result_msg}"
                )

            # Highlight last action failure to prevent repeating it
            if self.task_run.steps[-1].result and not self.task_run.steps[-1].result.success:
                last_fail = self.task_run.steps[-1]
                parts.append("")
                parts.append(f"\u26a0\ufe0f LAST ACTION FAILED: {last_fail.result.message}")
                parts.append("Try a DIFFERENT approach. Do NOT repeat the same action that just failed.")
                # If the failure was due to stale refs, emphasize current available refs
                if "not found in current snapshot" in last_fail.result.message:
                    current_refs = [el.ref for el in snapshot.elements if el.visible]
                    parts.append(f"Current valid refs: {', '.join(current_refs)}")
                    parts.append("You MUST use one of these refs above, not any ref from previous steps.")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Decision parsing
    # ------------------------------------------------------------------

    def _parse_decision(self, data: dict) -> ActionDecision:
        """Parse a dict into an ActionDecision, with safe defaults."""
        # Fix common invalid kind values from the LLM
        kind_fixes = {
            "search": "click",          # LLM often says "search" instead of clicking search btn
            "submit": "click",
            "type": "fill",
            "enter": "press_key",
            "goto": "navigate",
            "go": "navigate",
            "open": "navigate",
            "date": "select_date",
            "pick_date": "select_date",
            "calendar": "select_date",
        }
        if isinstance(data.get("kind"), str):
            fixed = kind_fixes.get(data["kind"].lower())
            if fixed:
                logger.info(f"Fixing action kind: '{data['kind']}' -> '{fixed}'")
                data["kind"] = fixed

        # Fill in defaults for commonly-omitted required fields
        if "reason" not in data or not data["reason"]:
            data["reason"] = data.get("user_visible_message", "")
        if "confidence" not in data or data["confidence"] is None:
            data["confidence"] = 0.5
        if "risk" not in data or not data["risk"]:
            data["risk"] = "safe"
        if "user_visible_message" not in data or not data["user_visible_message"]:
            data["user_visible_message"] = data.get("reason", "")

        try:
            return ActionDecision(**data)
        except Exception as e:
            logger.warning(f"Failed to parse decision: {e}, data: {data}")
            return ActionDecision(
                kind="stuck",
                reason=f"Failed to parse LLM response: {e}",
                confidence=0.0,
                risk="safe",
                user_visible_message=(
                    "I'm having trouble understanding what to do next."
                ),
            )

    # ------------------------------------------------------------------
    # Step recording
    # ------------------------------------------------------------------

    def _add_step(
        self, decision: ActionDecision, result: ActionResult | None
    ) -> None:
        """Add a step to the task run."""
        step = WebTaskStep(
            step_number=len(self.task_run.steps) + 1,
            decision=decision,
            result=result,
            sponsor_logs=[],
        )
        self.task_run.steps.append(step)
