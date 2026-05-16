"use client";

import { useState } from "react";
import { Send, CheckCircle2, RotateCcw } from "lucide-react";

interface FormData {
  name: string;
  email: string;
  phone: string;
  date_of_birth: string;
  address: string;
}

const INITIAL_DATA: FormData = {
  name: "",
  email: "",
  phone: "",
  date_of_birth: "",
  address: "",
};

export default function SmokeFormPage() {
  const [formData, setFormData] = useState<FormData>(INITIAL_DATA);
  const [submitted, setSubmitted] = useState(false);

  function handleChange(field: keyof FormData, value: string) {
    setFormData((prev) => ({ ...prev, [field]: value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitted(true);
  }

  function handleReset() {
    setFormData(INITIAL_DATA);
    setSubmitted(false);
  }

  const fields: { key: keyof FormData; label: string; type?: string }[] = [
    { key: "name", label: "Full Name" },
    { key: "email", label: "Email", type: "email" },
    { key: "phone", label: "Phone", type: "tel" },
    { key: "date_of_birth", label: "Date of Birth", type: "date" },
    { key: "address", label: "Address" },
  ];

  return (
    <div className="max-w-lg mx-auto px-4 py-8 md:px-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-mano-text mb-1">Smoke Test Form</h1>
          <p className="text-sm text-mano-muted">Internal QA form for testing the form-filling agent</p>
        </div>
        <button
          onClick={handleReset}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-mano-surface border border-mano-border text-mano-muted hover:text-mano-text transition-colors text-xs"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Reset
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {fields.map(({ key, label, type }) => (
          <div key={key}>
            <label className="block text-xs text-mano-muted mb-1.5">{label}</label>
            <input
              type={type || "text"}
              value={formData[key]}
              onChange={(e) => handleChange(key, e.target.value)}
              className="w-full bg-mano-surface border border-mano-border rounded-lg px-3 py-2.5 text-sm text-mano-text placeholder-mano-muted focus:outline-none focus:border-mano-primary transition-colors"
              placeholder={label}
            />
          </div>
        ))}

        <button
          type="submit"
          className="w-full py-2.5 bg-mano-primary hover:bg-mano-primary/80 text-white font-semibold rounded-lg transition-colors text-sm flex items-center justify-center gap-2"
        >
          <Send className="w-4 h-4" />
          Submit
        </button>
      </form>

      {submitted && (
        <div className="mt-6 rounded-xl border border-green-500/30 bg-green-900/10 p-4">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 className="w-5 h-5 text-green-400" />
            <h2 className="text-sm font-semibold text-green-400">Submitted Data</h2>
          </div>
          <pre className="text-xs text-mano-text bg-mano-darker rounded-lg p-3 overflow-x-auto">
            {JSON.stringify(formData, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
