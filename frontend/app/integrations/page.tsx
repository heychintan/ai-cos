"use client";
import { useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const SERVICES = [
  { key: "anthropic", label: "Anthropic (Claude)", placeholder: "sk-ant-..." },
  { key: "luma", label: "Luma Events", placeholder: "Your Luma API key" },
  { key: "spotify", label: "Spotify", placeholder: "Client ID / Secret in .env" },
  { key: "webflow", label: "Webflow CMS", placeholder: "Your Webflow API key" },
];

type TestResult = Record<string, { ok: boolean; message: string }>;

export default function IntegrationsPage() {
  const [results, setResults] = useState<TestResult>({});
  const [testing, setTesting] = useState<string | null>(null);

  const testConnection = async (service: string) => {
    setTesting(service);
    const form = new FormData();
    form.append("service", service);
    const res = await fetch(`${API}/api/test-connection`, { method: "POST", body: form });
    const data = await res.json();
    setResults((prev) => ({ ...prev, [service]: data }));
    setTesting(null);
  };

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Integrations</h1>
            <p className="text-sm text-gray-500 mt-1">
              API keys are loaded from <code className="bg-gray-100 px-1 rounded">.env</code> at the repo root
            </p>
          </div>
          <Link href="/" className="text-sm text-gray-500 hover:text-gray-900">← Automations</Link>
        </div>

        <div className="space-y-4">
          {SERVICES.map(({ key, label, placeholder }) => {
            const result = results[key];
            return (
              <div key={key} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">{label}</p>
                    <p className="text-xs text-gray-400 mt-0.5">{placeholder}</p>
                  </div>
                  <button
                    onClick={() => testConnection(key)}
                    disabled={testing === key}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition"
                  >
                    {testing === key ? "Testing…" : "Test Connection"}
                  </button>
                </div>
                {result && (
                  <p className={`mt-3 text-xs ${result.ok ? "text-green-600" : "text-red-600"}`}>
                    {result.ok ? "✓ " : "✗ "}{result.message}
                  </p>
                )}
              </div>
            );
          })}
        </div>

        <p className="mt-6 text-xs text-gray-400">
          Update <code className="bg-gray-100 px-1 rounded">.env</code> in the repo root, then restart the backend to pick up new keys.
        </p>
      </div>
    </main>
  );
}
