"use client";

import { useState } from "react";
import type { WebTaskRun, TaskStatus } from "@/lib/types";
import {
  CheckCircle2,
  AlertTriangle,
  Clock,
  Loader2,
  XCircle,
  AlertCircle,
  Send,
  Square,
  Sparkles,
} from "lucide-react";

const STATUS_CONFIG: Record<TaskStatus, { color: string; icon: typeof Loader2; label: string; pulse: boolean }> = {
  running: { color: "text-blue-400", icon: Loader2, label: "Running", pulse: true },
  waiting_for_user: { color: "text-yellow-400", icon: Clock, label: "Waiting for you", pulse: true },
  waiting_for_approval: { color: "text-amber-400", icon: AlertTriangle, label: "Needs approval", pulse: true },
  done: { color: "text-green-400", icon: CheckCircle2, label: "Done", pulse: false },
  stuck: { color: "text-orange-400", icon: AlertCircle, label: "Stuck", pulse: false },
  failed: { color: "text-red-400", icon: XCircle, label: "Failed", pulse: false },
};

interface RightPanelProps {
  task: WebTaskRun | null;
  onApprove: () => void;
  onDeny: () => void;
  onUserInput: (input: string) => void;
  onStop: () => void;
}

export default function RightPanel({ task, onApprove, onDeny, onUserInput, onStop }: RightPanelProps) {
  const [userInput, setUserInput] = useState("");

  if (!task) {
    return (
      <div className="flex flex-col h-full">
        <div className="px-4 py-3 border-b border-mano-border">
          <span className="text-xs font-semibold text-mano-muted uppercase tracking-wider">
            Control
          </span>
        </div>
        <div className="flex-1 flex items-center justify-center p-6">
          <p className="text-sm text-mano-muted text-center">
            Start a task to see controls and status here.
          </p>
        </div>
      </div>
    );
  }

  const cfg = STATUS_CONFIG[task.status];
  const StatusIcon = cfg.icon;
  const isActive = ["running", "waiting_for_user", "waiting_for_approval"].includes(task.status);

  function handleUserInput() {
    if (!userInput.trim()) return;
    onUserInput(userInput.trim());
    setUserInput("");
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-mano-border">
        <span className="text-xs font-semibold text-mano-muted uppercase tracking-wider">
          Control
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Status badge */}
        <div className="rounded-lg bg-mano-surface px-3 py-3 flex items-center gap-3">
          <StatusIcon
            className={`w-5 h-5 ${cfg.pulse ? "animate-pulse-dot" : ""} ${cfg.color}`}
          />
          <div>
            <p className={`text-sm font-semibold ${cfg.color}`}>{cfg.label}</p>
            <p className="text-xs text-mano-muted">Step {task.steps.length}</p>
          </div>
        </div>

        {/* Current action */}
        {task.steps.length > 0 && (
          <div className="rounded-lg bg-mano-surface/50 px-3 py-2.5">
            <p className="text-xs text-mano-muted mb-1">Current action</p>
            <p className="text-xs text-mano-text">
              {task.steps[task.steps.length - 1].decision.user_visible_message}
            </p>
          </div>
        )}

        {/* Approval section */}
        {task.requires_approval && task.approval_reason && (
          <div className="rounded-xl border border-amber-500/40 bg-amber-900/15 px-4 py-3">
            <p className="text-sm text-amber-400 font-semibold mb-1">
              Approval Required
            </p>
            <p className="text-xs text-mano-text mb-3">{task.approval_reason}</p>
            <div className="flex gap-2">
              <button
                onClick={onApprove}
                className="flex-1 py-2 bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold rounded-lg transition-colors"
              >
                Approve
              </button>
              <button
                onClick={onDeny}
                className="flex-1 py-2 bg-mano-surface hover:bg-red-900/40 text-mano-text text-xs font-semibold rounded-lg transition-colors"
              >
                Deny
              </button>
            </div>
          </div>
        )}

        {/* User input section */}
        {task.status === "waiting_for_user" && (
          <div className="rounded-xl border border-yellow-500/40 bg-yellow-900/10 px-4 py-3">
            <p className="text-sm text-yellow-400 font-semibold mb-1">
              Question for you
            </p>
            <p className="text-xs text-mano-text mb-3">
              {task.steps.at(-1)?.decision.question || "The agent needs your input."}
            </p>
            <div className="flex gap-2">
              <input
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") handleUserInput(); }}
                placeholder="Type your answer..."
                className="flex-1 bg-mano-darker border border-mano-border rounded-lg px-3 py-2 text-xs text-mano-text placeholder-mano-muted focus:outline-none focus:border-mano-primary"
              />
              <button
                onClick={handleUserInput}
                disabled={!userInput.trim()}
                className="px-3 py-2 bg-mano-primary hover:bg-mano-primary/80 disabled:opacity-40 rounded-lg transition-colors"
              >
                <Send className="w-3.5 h-3.5 text-white" />
              </button>
            </div>
          </div>
        )}

        {/* Final answer */}
        {task.status === "done" && task.final_answer && (
          <div className="rounded-xl border border-green-500/30 bg-green-900/10 px-4 py-3">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-green-400" />
              <p className="text-sm text-green-400 font-semibold">Final Answer</p>
            </div>
            <p className="text-sm text-mano-text leading-relaxed">{task.final_answer}</p>
          </div>
        )}

        {/* Stop button */}
        {isActive && (
          <button
            onClick={onStop}
            className="w-full py-2.5 bg-mano-surface hover:bg-red-900/30 border border-mano-border hover:border-red-500/30 text-mano-text text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <Square className="w-4 h-4" />
            Stop Task
          </button>
        )}
      </div>
    </div>
  );
}
