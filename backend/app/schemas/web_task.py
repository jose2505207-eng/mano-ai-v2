from typing import Literal

from pydantic import BaseModel, Field

RiskLevel = Literal["safe", "caution", "sensitive", "blocked"]


class UserProfile(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    date_of_birth: str | None = None
    address: str | None = None
    preferred_language: Literal["en", "es"] = "en"
    preferred_airport: str | None = None
    payment_allowed: bool = False


class TaskConstraints(BaseModel):
    budget: str | None = None
    location: str | None = None
    date_range: str | None = None
    must_ask_before_submit: bool = True
    must_ask_before_payment: bool = True
    allow_account_creation: bool = False
    allow_sensitive_fields: bool = False


class BrowserElement(BaseModel):
    ref: str
    role: str | None = None
    tag: str | None = None
    text: str | None = None
    name: str | None = None
    value: str | None = None
    placeholder: str | None = None
    input_type: str | None = None
    visible: bool = True


class BrowserSnapshot(BaseModel):
    url: str
    title: str | None = None
    text_summary: str
    elements: list[BrowserElement] = []
    screenshot: str | None = None


class ActionDecision(BaseModel):
    kind: Literal[
        "navigate",
        "search_web",
        "click",
        "fill",
        "select",
        "scroll",
        "wait",
        "extract",
        "ask_user",
        "request_approval",
        "done",
        "stuck",
    ]
    ref: str | None = None
    value: str | None = None
    url: str | None = None
    question: str | None = None
    reason: str
    confidence: float = Field(ge=0, le=1)
    risk: RiskLevel
    user_visible_message: str


class ActionResult(BaseModel):
    success: bool
    message: str
    screenshot: str | None = None
    snapshot_summary: str | None = None


class SponsorLog(BaseModel):
    provider: str
    action: str
    status: Literal["connected", "fallback", "not_configured", "error"]
    details: str | None = None
    timestamp: str


class WebTaskStep(BaseModel):
    step_number: int
    decision: ActionDecision
    result: ActionResult | None = None
    sponsor_logs: list[SponsorLog] = []


class WebTaskRun(BaseModel):
    task_id: str
    task: str
    status: Literal[
        "running",
        "waiting_for_user",
        "waiting_for_approval",
        "done",
        "stuck",
        "failed",
    ]
    steps: list[WebTaskStep] = []
    final_answer: str | None = None
    current_url: str | None = None
    requires_approval: bool = False
    approval_reason: str | None = None
