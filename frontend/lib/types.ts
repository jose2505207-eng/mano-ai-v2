export type RiskLevel = "safe" | "caution" | "sensitive" | "blocked";
export type TaskStatus = "running" | "waiting_for_user" | "waiting_for_approval" | "done" | "stuck" | "failed";
export type ActionKind = "navigate" | "search_web" | "click" | "fill" | "select" | "scroll" | "wait" | "extract" | "ask_user" | "request_approval" | "done" | "stuck";

export interface UserProfile {
  full_name: string | null;
  email: string | null;
  phone: string | null;
  date_of_birth: string | null;
  address: string | null;
  preferred_language: "en" | "es";
  preferred_airport: string | null;
  payment_allowed: boolean;
}

export interface TaskConstraints {
  budget: string | null;
  location: string | null;
  date_range: string | null;
  must_ask_before_submit: boolean;
  must_ask_before_payment: boolean;
  allow_account_creation: boolean;
  allow_sensitive_fields: boolean;
}

export interface BrowserElement {
  ref: string;
  role: string | null;
  tag: string | null;
  text: string | null;
  name: string | null;
  value: string | null;
  placeholder: string | null;
  input_type: string | null;
  visible: boolean;
}

export interface BrowserSnapshot {
  url: string;
  title: string | null;
  text_summary: string;
  elements: BrowserElement[];
  screenshot: string | null;
}

export interface ActionDecision {
  kind: ActionKind;
  ref: string | null;
  value: string | null;
  url: string | null;
  question: string | null;
  reason: string;
  confidence: number;
  risk: RiskLevel;
  user_visible_message: string;
}

export interface ActionResult {
  success: boolean;
  message: string;
  screenshot: string | null;
  snapshot_summary: string | null;
}

export interface SponsorLog {
  provider: string;
  action: string;
  status: "connected" | "fallback" | "not_configured" | "error";
  details: string | null;
  timestamp: string;
}

export interface WebTaskStep {
  step_number: number;
  decision: ActionDecision;
  result: ActionResult | null;
  sponsor_logs: SponsorLog[];
}

export interface WebTaskRun {
  task_id: string;
  task: string;
  status: TaskStatus;
  steps: WebTaskStep[];
  final_answer: string | null;
  current_url: string | null;
  requires_approval: boolean;
  approval_reason: string | null;
}

export interface SponsorStatus {
  name: string;
  status: "connected" | "fallback" | "not_configured" | "error";
  details: string | null;
}

export interface HealthResponse {
  ok: boolean;
  app: string;
  mode: string;
}
