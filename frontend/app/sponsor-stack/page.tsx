"use client";

import { useEffect, useState } from "react";
import { getSponsorStatus } from "@/lib/api";
import type { SponsorStatus } from "@/lib/types";
import { CheckCircle2, AlertTriangle, XCircle, HelpCircle, Loader2 } from "lucide-react";

const SPONSOR_INFO: Record<string, { description: string; color: string }> = {
  "Bright Data": { description: "Web data infrastructure & SERP API", color: "bg-green-500" },
  "AgentField": { description: "AI agent orchestration platform", color: "bg-blue-500" },
  "Nosana": { description: "Decentralized GPU compute network", color: "bg-purple-500" },
  "Actionbook": { description: "Browser action manuals & automation", color: "bg-cyan-500" },
  "EverMind": { description: "Persistent AI memory & context", color: "bg-amber-500" },
  "Qwen Cloud": { description: "Large language model provider", color: "bg-indigo-500" },
  "Zeabur": { description: "One-click cloud deployment", color: "bg-orange-500" },
  "Z.ai": { description: "Advanced AI language models", color: "bg-rose-500" },
  "Qoder": { description: "AI-powered coding assistant", color: "bg-violet-500" },
  "TokenRouter": { description: "Intelligent LLM request routing", color: "bg-teal-500" },
  "Butterbase": { description: "Backend-as-a-service & data persistence", color: "bg-yellow-500" },
};

const STATUS_CONFIG: Record<string, { icon: typeof CheckCircle2; color: string; badge: string }> = {
  connected: { icon: CheckCircle2, color: "text-green-400", badge: "bg-green-900/40 text-green-300" },
  fallback: { icon: AlertTriangle, color: "text-yellow-400", badge: "bg-yellow-900/40 text-yellow-300" },
  not_configured: { icon: HelpCircle, color: "text-slate-400", badge: "bg-slate-700/40 text-slate-400" },
  error: { icon: XCircle, color: "text-red-400", badge: "bg-red-900/40 text-red-300" },
};

export default function SponsorStackPage() {
  const [sponsors, setSponsors] = useState<SponsorStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSponsorStatus()
      .then((data) => setSponsors(data.sponsors))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load sponsors"))
      .finally(() => setLoading(false));
  }, []);

  // Merge API data with static sponsor info, ensuring all 11 sponsors show
  const sponsorMap = new Map(sponsors.map((s) => [s.name, s]));
  const allSponsors = Object.keys(SPONSOR_INFO).map((name) => {
    const apiData = sponsorMap.get(name);
    return {
      name,
      ...SPONSOR_INFO[name],
      status: apiData?.status || ("not_configured" as const),
      details: apiData?.details || null,
    };
  });

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 md:px-6">
      <h1 className="text-2xl font-bold text-mano-text mb-1">Sponsor Stack</h1>
      <p className="text-sm text-mano-muted mb-6">
        The technology partners powering Mano AI
      </p>

      {loading && (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-mano-primary" />
        </div>
      )}

      {error && (
        <div className="px-4 py-3 rounded-lg bg-red-900/20 border border-red-500/30 text-red-400 text-sm mb-6">
          {error}
        </div>
      )}

      {!loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {allSponsors.map((sponsor) => {
            const statusCfg = STATUS_CONFIG[sponsor.status] || STATUS_CONFIG.not_configured;
            const StatusIcon = statusCfg.icon;

            return (
              <div
                key={sponsor.name}
                className="rounded-xl border border-mano-border bg-mano-surface/50 p-5 hover:border-mano-border/80 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-lg ${sponsor.color} flex items-center justify-center flex-shrink-0`}>
                      <span className="text-white font-bold text-sm">
                        {sponsor.name.charAt(0)}
                      </span>
                    </div>
                    <div>
                      <h2 className="text-sm font-semibold text-mano-text">{sponsor.name}</h2>
                    </div>
                  </div>
                </div>
                <p className="text-xs text-mano-muted mb-3">{sponsor.description}</p>
                <div className="flex items-center gap-2">
                  <StatusIcon className={`w-3.5 h-3.5 ${statusCfg.color}`} />
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${statusCfg.badge}`}>
                    {sponsor.status.replace("_", " ")}
                  </span>
                </div>
                {sponsor.details && (
                  <p className="text-[11px] text-mano-muted mt-2 truncate">{sponsor.details}</p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
