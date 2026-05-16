"use client";

import type { TaskStatus } from "@/lib/types";
import { Globe, Loader2 } from "lucide-react";

interface BrowserPanelProps {
  currentUrl: string | null;
  screenshot: string | null;
  status: TaskStatus;
}

export default function BrowserPanel({ currentUrl, screenshot, status }: BrowserPanelProps) {
  const isRunning = status === "running";

  return (
    <div className="flex flex-col h-full">
      {/* Mini address bar */}
      <div className="px-4 py-3 border-b border-mano-border">
        <div className="flex items-center gap-2 bg-mano-surface rounded-lg px-3 py-1.5">
          <Globe className="w-3.5 h-3.5 text-mano-muted flex-shrink-0" />
          <span className="text-xs text-blue-300 truncate flex-1">
            {currentUrl || "No page loaded"}
          </span>
        </div>
      </div>

      {/* Browser viewport */}
      <div className="flex-1 relative overflow-hidden p-4">
        {screenshot ? (
          <div className="relative rounded-xl overflow-hidden border border-mano-border">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={screenshot.startsWith("data:") ? screenshot : `data:image/jpeg;base64,${screenshot}`}
              alt="Browser screenshot"
              className="w-full"
            />
            {isRunning && (
              <div className="absolute inset-0 bg-mano-darker/40 flex items-center justify-center">
                <div className="flex items-center gap-2 bg-mano-surface/90 rounded-lg px-4 py-2">
                  <Loader2 className="w-4 h-4 animate-spin text-mano-primary" />
                  <span className="text-xs text-mano-text font-medium">
                    Mano AI is browsing...
                  </span>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="rounded-xl bg-mano-surface/30 border border-mano-border/50 h-full min-h-[200px] flex flex-col items-center justify-center gap-3">
            <Globe className="w-12 h-12 text-mano-border" />
            <p className="text-sm text-mano-muted">Browser view</p>
            <p className="text-xs text-mano-border">
              Screenshots will appear here as the agent navigates
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
