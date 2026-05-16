"use client";

import { useState } from "react";
import { Languages, Shield, Code, Info } from "lucide-react";

export default function SettingsPage() {
  const [lang, setLang] = useState<"en" | "es">("en");
  const [askBeforeSubmit, setAskBeforeSubmit] = useState(true);
  const [askBeforePayment, setAskBeforePayment] = useState(true);
  const [askBeforePersonalInfo, setAskBeforePersonalInfo] = useState(true);
  const [apiUrl, setApiUrl] = useState(
    typeof window !== "undefined"
      ? localStorage.getItem("mano_api_url") || (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
      : "http://localhost:8000"
  );
  const [saved, setSaved] = useState(false);

  function handleSaveApiUrl() {
    if (typeof window !== "undefined") {
      localStorage.setItem("mano_api_url", apiUrl);
    }
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  function Toggle({ checked, onChange, label, description }: {
    checked: boolean;
    onChange: (v: boolean) => void;
    label: string;
    description: string;
  }) {
    return (
      <div className="flex items-start gap-3 py-2">
        <button
          role="switch"
          aria-checked={checked}
          onClick={() => onChange(!checked)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors flex-shrink-0 mt-0.5 ${
            checked ? "bg-mano-primary" : "bg-mano-border"
          }`}
        >
          <span
            className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
              checked ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
        <div>
          <p className="text-sm text-mano-text">{label}</p>
          <p className="text-xs text-mano-muted">{description}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-8 md:px-6">
      <h1 className="text-2xl font-bold text-mano-text mb-1">Settings</h1>
      <p className="text-sm text-mano-muted mb-6">
        Configure Mano AI behavior. Changes apply to the next task.
      </p>

      <div className="space-y-6">
        {/* Language */}
        <div className="rounded-xl border border-mano-border/50 bg-mano-surface/30 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Languages className="w-4 h-4 text-mano-primary" />
            <h2 className="text-sm font-semibold text-mano-text">Language Preference</h2>
          </div>
          <select
            value={lang}
            onChange={(e) => setLang(e.target.value as "en" | "es")}
            className="w-full bg-mano-surface border border-mano-border rounded-lg px-3 py-2.5 text-sm text-mano-text focus:outline-none focus:border-mano-primary transition-colors"
          >
            <option value="en">English</option>
            <option value="es">Español</option>
          </select>
        </div>

        {/* Safety */}
        <div className="rounded-xl border border-mano-border/50 bg-mano-surface/30 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="w-4 h-4 text-mano-primary" />
            <h2 className="text-sm font-semibold text-mano-text">Safety Preferences</h2>
          </div>
          <div className="space-y-1">
            <Toggle
              checked={askBeforeSubmit}
              onChange={setAskBeforeSubmit}
              label="Ask before submitting forms"
              description="Mano AI will pause and ask you before submitting any form"
            />
            <Toggle
              checked={askBeforePayment}
              onChange={setAskBeforePayment}
              label="Ask before payments"
              description="Always require explicit approval before any payment action"
            />
            <Toggle
              checked={askBeforePersonalInfo}
              onChange={setAskBeforePersonalInfo}
              label="Ask before sharing personal info"
              description="Pause before filling sensitive fields like SSN or date of birth"
            />
          </div>
        </div>

        {/* API URL */}
        <div className="rounded-xl border border-mano-border/50 bg-mano-surface/30 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Code className="w-4 h-4 text-mano-primary" />
            <h2 className="text-sm font-semibold text-mano-text">API Configuration</h2>
          </div>
          <label className="block text-xs text-mano-muted mb-1.5">Backend API URL</label>
          <div className="flex gap-2">
            <input
              type="url"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              className="flex-1 bg-mano-surface border border-mano-border rounded-lg px-3 py-2 text-xs text-mano-text font-mono focus:outline-none focus:border-mano-primary transition-colors"
            />
            <button
              onClick={handleSaveApiUrl}
              className="px-3 py-2 bg-mano-primary hover:bg-mano-primary/80 text-white text-xs font-semibold rounded-lg transition-colors"
            >
              {saved ? "Saved!" : "Save"}
            </button>
          </div>
          <p className="text-xs text-mano-border mt-2">For development only. Requires page reload.</p>
        </div>

        {/* About */}
        <div className="rounded-xl border border-mano-border/50 bg-mano-surface/30 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Info className="w-4 h-4 text-mano-primary" />
            <h2 className="text-sm font-semibold text-mano-text">About Mano AI</h2>
          </div>
          <p className="text-sm text-mano-text mb-2">
            The internet, guided step by step.
          </p>
          <p className="text-xs text-mano-muted leading-relaxed">
            Mano AI is a safety-first, bilingual browser agent designed for people with low
            computer skills. It navigates the web on your behalf, always asking before taking
            sensitive actions.
          </p>
          <div className="mt-3 pt-3 border-t border-mano-border/30">
            <p className="text-xs text-mano-border">Version 0.1.0</p>
          </div>
        </div>
      </div>
    </div>
  );
}
