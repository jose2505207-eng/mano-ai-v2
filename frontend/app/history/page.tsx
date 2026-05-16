"use client";

import { useEffect, useState } from "react";
import { getLogs } from "@/lib/api";
import type { WebTaskRun } from "@/lib/types";
import { Clock, ChevronDown, ChevronRight, Loader2, Inbox } from "lucide-react";

interface LogEntry {
  task_id: string;
  task: string;
  status: string;
  steps: { step_number: number }[];
  timestamp: string;
}

export default function HistoryPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    getLogs()
      .then((data) => setLogs(data as LogEntry[]))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load history"))
      .finally(() => setLoading(false));
  }, []);

  const statusColor: Record<string, string> = {
    done: "text-green-400",
    failed: "text-red-400",
    stuck: "text-orange-400",
    running: "text-blue-400",
    waiting_for_user: "text-yellow-400",
    waiting_for_approval: "text-amber-400",
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 className="w-6 h-6 animate-spin text-mano-primary" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 md:px-6">
      <h1 className="text-2xl font-bold text-mano-text mb-1">Task History</h1>
      <p className="text-sm text-mano-muted mb-6">
        Your recent Mano AI sessions
      </p>

      {error && (
        <div className="px-4 py-3 rounded-lg bg-red-900/20 border border-red-500/30 text-red-400 text-sm mb-6">
          {error}
        </div>
      )}

      {logs.length === 0 && !error ? (
        <div className="rounded-xl bg-mano-surface/30 border border-mano-border/50 p-12 text-center">
          <Inbox className="w-12 h-12 text-mano-border mx-auto mb-3" />
          <p className="text-mano-muted text-sm">No tasks yet. Start by telling Mano AI what you need!</p>
        </div>
      ) : (
        <div className="space-y-2">
          {logs.map((log) => {
            const isExpanded = expandedId === log.task_id;
            return (
              <div
                key={log.task_id}
                className="rounded-xl border border-mano-border/50 bg-mano-surface/30 overflow-hidden"
              >
                <button
                  onClick={() => setExpandedId(isExpanded ? null : log.task_id)}
                  className="w-full px-4 py-3 flex items-center gap-3 hover:bg-mano-surface/50 transition-colors text-left"
                >
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-mano-muted flex-shrink-0" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-mano-muted flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-mano-text truncate">{log.task}</p>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className={`text-xs font-medium ${statusColor[log.status] || "text-mano-muted"}`}>
                        {log.status.replace(/_/g, " ")}
                      </span>
                      <span className="text-xs text-mano-muted flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {log.steps?.length || 0} steps
                      </span>
                      {log.timestamp && (
                        <span className="text-xs text-mano-border">
                          {new Date(log.timestamp).toLocaleString()}
                        </span>
                      )}
                    </div>
                  </div>
                </button>
                {isExpanded && log.steps && log.steps.length > 0 && (
                  <div className="px-4 pb-3 border-t border-mano-border/30 pt-2">
                    {(log.steps as unknown as WebTaskRun["steps"]).map((step) => (
                      <div key={step.step_number} className="flex items-center gap-2 py-1">
                        <span className="text-xs text-mano-muted w-12">#{step.step_number}</span>
                        <span className="text-xs text-mano-text">
                          {step.decision?.user_visible_message || `Step ${step.step_number}`}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
