import { WebTaskRun, UserProfile, HealthResponse, SponsorStatus } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL || (typeof window !== "undefined" && window.location.hostname !== "localhost" ? "" : "http://localhost:8000");

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

export async function getHealth(): Promise<HealthResponse> {
  return request("/api/health");
}

export async function getSponsorStatus(): Promise<{ sponsors: SponsorStatus[] }> {
  return request("/api/sponsor-status");
}

export async function startTask(task: string, language?: string, profile?: Partial<UserProfile>): Promise<WebTaskRun> {
  return request("/api/tasks", {
    method: "POST",
    body: JSON.stringify({ task, language: language || "en", profile }),
  });
}

export async function getTask(taskId: string): Promise<WebTaskRun> {
  return request(`/api/tasks/${taskId}`);
}

export async function continueTask(taskId: string, userInput: string): Promise<WebTaskRun> {
  return request(`/api/tasks/${taskId}/continue`, {
    method: "POST",
    body: JSON.stringify({ user_input: userInput }),
  });
}

export async function approveTask(taskId: string): Promise<WebTaskRun> {
  return request(`/api/tasks/${taskId}/continue`, {
    method: "POST",
    body: JSON.stringify({ approved: true }),
  });
}

export async function stopTask(taskId: string): Promise<WebTaskRun> {
  return request(`/api/tasks/${taskId}/stop`, { method: "POST" });
}

export async function getTaskSnapshot(taskId: string): Promise<unknown> {
  return request(`/api/tasks/${taskId}/snapshot`);
}

export async function getProfile(): Promise<UserProfile> {
  return request("/api/profile");
}

export async function updateProfile(profile: Partial<UserProfile>): Promise<UserProfile> {
  return request("/api/profile", {
    method: "POST",
    body: JSON.stringify(profile),
  });
}

export async function getLogs(): Promise<unknown[]> {
  return request("/api/logs");
}
