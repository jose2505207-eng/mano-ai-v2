"use client";

import { useEffect, useRef } from "react";
import type { WebTaskStep, TaskStatus, RiskLevel } from "@/lib/types";
import { Shield, AlertTriangle, Ban, CheckCircle2, Loader2 } from "lucide-react";

const RISK_CONFIG: Record<RiskLevel, { bg: string; text: string; icon: typeof Shield }> = {
  safe: { bg: "bg-green-900/30", text: "text-green-400", icon: CheckCircle2 },
  caution: { bg: "bg-yellow-900/30", text: "text-yellow-400", icon: AlertTriangle },
  sensitive: { bg: "bg-orange-900/30", text: "text-orange-400", icon: Shield },
  blocked: { bg: "bg-red-900/30", text: "text-red-400", icon: Ban },
};

const KIND_BADGE: Record<string, string> = {
  navigate: "bg-blue-900/40 text-blue-300",
  search_web: "bg-cyan-900/40 text-cyan-300",
  click: "bg-purple-900/40 text-purple-300",
  fill: "bg-indigo-900/40 text-indigo-300",
  select: "bg-violet-900/40 text-violet-300",
  scroll: "bg-slate-700/40 text-slate-300",
  wait: "bg-slate-700/40 text-slate-300",
  extract: "bg-teal-900/40 text-teal-300",
  ask_user: "bg-amber-900/40 text-amber-300",
  request_approval: "bg-amber-900/40 text-amber-300",
  done: "bg-green-900/40 text-green-300",
  stuck: "bg-red-900/40 text-red-300",
};

interface ChatPanelProps {
  steps: WebTaskStep[];
  status: TaskStatus;
}

export default function ChatPanel({ steps, status }: ChatPanelProps) {
  const safeSteps = steps || [];
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [safeSteps.length]);

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-mano-border">
        <span className="text-xs font-semibold text-mano-muted uppercase tracking-wider">
          Task Steps
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {safeSteps.length === 0 && status === "running" && (
          <div className="flex items-center gap-2 text-mano-muted text-sm py-8 justify-center">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Thinking...</span>
          </div>
        )}

        {safeSteps.length === 0 && status !== "running" && (
          <div className="text-mano-muted text-sm text-center py-8">
            Steps will appear here as the agent works.
          </div>
        )}

        {safeSteps.map((step) => {
          const risk = step.decision.risk;
          const riskCfg = RISK_CONFIG[risk];
          const RiskIcon = riskCfg.icon;
          const kindBadge = KIND_BADGE[step.decision.kind] || "bg-slate-700/40 text-slate-300";

          return (
            <div
              key={`step-${step.step_number}`}
              className="rounded-xl bg-mano-surface/50 border border-mano-border/50 overflow-hidden"
            >
              <div className="px-3 py-2 flex items-center gap-2 border-b border-mano-border/30">
                <span className="text-xs text-mano-muted font-medium">
                  Step {step.step_number}
                </span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${kindBadge}`}>
                  {step.decision.kind}
                </span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium flex items-center gap-1 ${riskCfg.bg} ${riskCfg.text}`}>
                  <RiskIcon className="w-3 h-3" />
                  {risk}
                </span>
              </div>
              <div className="px-3 py-2.5">
                <p className="text-sm text-mano-text leading-relaxed">
                  {step.decision.user_visible_message}
                </p>
                {step.result && (
                  <p className={`text-xs mt-1.5 ${step.result.success ? "text-green-400" : "text-red-400"}`}>
                    {step.result.message}
                  </p>
                )}
              </div>
            </div>
          );
        })}

        {status === "running" && safeSteps.length > 0 && (
          <div className="flex items-center gap-2 text-mano-muted text-sm py-2 justify-center">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Working...</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
