"use client";

import { useEffect, useState } from "react";
import { getProfile, updateProfile } from "@/lib/api";
import type { UserProfile } from "@/lib/types";
import { Save, CheckCircle2, AlertTriangle, Plane } from "lucide-react";

const SENSITIVE_FIELDS = new Set(["date_of_birth", "phone"]);

const COMMON_AIRPORTS = [
  "SFO", "LAX", "SJC", "OAK", "GDL", "JFK", "ORD", "MIA", "DFW", "SEA",
];

const FORM_FIELDS: { key: keyof UserProfile; label: string; type?: string }[] = [
  { key: "full_name", label: "Full Name" },
  { key: "email", label: "Email", type: "email" },
  { key: "phone", label: "Phone", type: "tel" },
  { key: "date_of_birth", label: "Date of Birth", type: "date" },
  { key: "address", label: "Address" },
];

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [airportSearch, setAirportSearch] = useState("");

  useEffect(() => {
    getProfile()
      .then(setProfile)
      .catch(() => setToast({ type: "error", message: "Failed to load profile" }))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(null), 3000);
      return () => clearTimeout(t);
    }
  }, [toast]);

  async function handleSave() {
    if (!profile) return;
    setSaving(true);
    try {
      const updated = await updateProfile(profile);
      setProfile(updated);
      setToast({ type: "success", message: "Profile saved successfully!" });
    } catch {
      setToast({ type: "error", message: "Failed to save profile" });
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-mano-muted text-sm">Loading profile...</div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-center">
          <AlertTriangle className="w-8 h-8 text-amber-400 mx-auto mb-2" />
          <p className="text-mano-muted text-sm">Could not load profile</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto px-4 py-8 md:px-6">
      <h1 className="text-2xl font-bold text-mano-text mb-1">Your Profile</h1>
      <p className="text-sm text-mano-muted mb-6">
        Saved securely. Never auto-filled in payments, passwords, or government forms without your approval.
      </p>

      <div className="space-y-5">
        {FORM_FIELDS.map(({ key, label, type }) => (
          <div key={key}>
            <label className="block text-xs text-mano-muted mb-1.5">
              {label}
              {SENSITIVE_FIELDS.has(key) && (
                <span className="ml-2 text-yellow-500 text-[10px]">(caution — asked before use)</span>
              )}
            </label>
            <input
              type={type || "text"}
              value={String(profile[key] ?? "")}
              onChange={(e) => setProfile({ ...profile, [key]: e.target.value || null })}
              className="w-full bg-mano-surface border border-mano-border rounded-lg px-3 py-2.5 text-sm text-mano-text placeholder-mano-muted focus:outline-none focus:border-mano-primary transition-colors"
            />
          </div>
        ))}

        {/* Preferred Airport with suggestions */}
        <div>
          <label className="block text-xs text-mano-muted mb-1.5">
            <Plane className="w-3 h-3 inline mr-1" />
            Preferred Airport
          </label>
          <input
            type="text"
            value={airportSearch || profile.preferred_airport || ""}
            onChange={(e) => {
              setAirportSearch(e.target.value);
              setProfile({ ...profile, preferred_airport: e.target.value || null });
            }}
            placeholder="e.g. SFO"
            className="w-full bg-mano-surface border border-mano-border rounded-lg px-3 py-2.5 text-sm text-mano-text placeholder-mano-muted focus:outline-none focus:border-mano-primary transition-colors"
          />
          <div className="flex flex-wrap gap-1.5 mt-2">
            {COMMON_AIRPORTS
              .filter((a) => !airportSearch || a.includes(airportSearch.toUpperCase()))
              .slice(0, 6)
              .map((airport) => (
                <button
                  key={airport}
                  onClick={() => {
                    setProfile({ ...profile, preferred_airport: airport });
                    setAirportSearch(airport);
                  }}
                  className={`text-xs px-2.5 py-1 rounded-md border transition-colors ${
                    profile.preferred_airport === airport
                      ? "bg-mano-primary/15 border-mano-primary/30 text-mano-primary"
                      : "bg-mano-surface border-mano-border text-mano-muted hover:text-mano-text"
                  }`}
                >
                  {airport}
                </button>
              ))}
          </div>
        </div>

        {/* Preferred Language */}
        <div>
          <label className="block text-xs text-mano-muted mb-1.5">Preferred Language</label>
          <select
            value={profile.preferred_language}
            onChange={(e) => setProfile({ ...profile, preferred_language: e.target.value as "en" | "es" })}
            className="w-full bg-mano-surface border border-mano-border rounded-lg px-3 py-2.5 text-sm text-mano-text focus:outline-none focus:border-mano-primary transition-colors"
          >
            <option value="en">English</option>
            <option value="es">Español</option>
          </select>
        </div>

        {/* Payment allowed toggle */}
        <div className="flex items-center gap-3 py-2">
          <button
            role="switch"
            aria-checked={profile.payment_allowed}
            onClick={() => setProfile({ ...profile, payment_allowed: !profile.payment_allowed })}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              profile.payment_allowed ? "bg-mano-primary" : "bg-mano-border"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                profile.payment_allowed ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
          <label className="text-sm text-mano-muted">
            Allow payment-related actions
            <span className="block text-xs text-mano-border">Always requires explicit approval</span>
          </label>
        </div>

        {/* Save button */}
        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full py-2.5 bg-mano-primary hover:bg-mano-primary/80 disabled:opacity-50 text-white font-semibold rounded-lg transition-colors text-sm flex items-center justify-center gap-2"
        >
          {saving ? (
            "Saving..."
          ) : (
            <>
              <Save className="w-4 h-4" />
              Save Profile
            </>
          )}
        </button>
      </div>

      {/* Toast notification */}
      {toast && (
        <div className={`fixed bottom-20 md:bottom-6 right-6 px-4 py-3 rounded-lg border flex items-center gap-2 text-sm z-50 ${
          toast.type === "success"
            ? "bg-green-900/30 border-green-500/30 text-green-400"
            : "bg-red-900/30 border-red-500/30 text-red-400"
        }`}>
          {toast.type === "success" ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
          {toast.message}
        </div>
      )}
    </div>
  );
}
