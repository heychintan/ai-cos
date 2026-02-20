"use client";
import { useState, useRef } from "react";
import Link from "next/link";

const API = "http://localhost:8000";

type RunStatus = "idle" | "fetching" | "generating" | "done" | "error";

const STATUS_COLORS: Record<RunStatus, string> = {
  idle: "bg-gray-100 text-gray-600",
  fetching: "bg-blue-100 text-blue-700",
  generating: "bg-purple-100 text-purple-700",
  done: "bg-green-100 text-green-700",
  error: "bg-red-100 text-red-700",
};

const STATUS_LABELS: Record<RunStatus, string> = {
  idle: "Never Run",
  fetching: "Fetching Data…",
  generating: "Generating…",
  done: "Success",
  error: "Failed",
};

export default function AutomationsPage() {
  const [status, setStatus] = useState<RunStatus>("idle");
  const [step, setStep] = useState("");
  const [error, setError] = useState("");
  const templateRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const pollStatus = () => {
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/status`);
        const data = await res.json();
        setStatus(data.status);
        setStep(data.step);
        if (data.status === "done" || data.status === "error") {
          clearInterval(pollRef.current!);
          if (data.error) setError(data.error);
        }
      } catch {}
    }, 1000);
  };

  const handleRun = async () => {
    setStatus("fetching");
    setStep("Starting…");
    setError("");

    const form = new FormData();
    if (templateRef.current?.files?.[0]) {
      form.append("template", templateRef.current.files[0]);
    }

    pollStatus();

    try {
      const res = await fetch(`${API}/api/run`, { method: "POST", body: form });
      clearInterval(pollRef.current!);

      if (!res.ok) {
        const err = await res.json();
        setStatus("error");
        setError(err.detail || "Unknown error");
        return;
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const disposition = res.headers.get("Content-Disposition") || "";
      const match = disposition.match(/filename="(.+)"/);
      a.download = match ? match[1] : "newsletter.docx";
      a.click();
      URL.revokeObjectURL(url);
      setStatus("done");
      setStep("Done!");
    } catch (e: unknown) {
      clearInterval(pollRef.current!);
      setStatus("error");
      setError(e instanceof Error ? e.message : "Network error");
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">CoSN Agent Dashboard</h1>
            <p className="text-sm text-gray-500 mt-1">Content automation for Chief of Staff Network</p>
          </div>
          <nav className="flex gap-4 text-sm">
            <Link href="/integrations" className="text-gray-500 hover:text-gray-900">Integrations</Link>
          </nav>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="p-6 flex items-start justify-between">
            <div>
              <h2 className="font-semibold text-gray-900">Weekly Newsletter Draft</h2>
              <p className="text-sm text-gray-500 mt-1">
                Pulls from Luma, Spotify &amp; Webflow → generates .docx via Claude
              </p>
              <span className={`inline-block mt-3 px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[status]}`}>
                {STATUS_LABELS[status]}
              </span>
            </div>
            <button
              onClick={handleRun}
              disabled={status === "fetching" || status === "generating"}
              className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {status === "fetching" || status === "generating" ? "Running…" : "Run Now"}
            </button>
          </div>

          <div className="border-t border-gray-100 px-6 py-4">
            <label className="text-xs font-medium text-gray-500 block mb-1">
              Template override (optional .md or .txt)
            </label>
            <input
              ref={templateRef}
              type="file"
              accept=".md,.txt"
              className="text-sm text-gray-600 file:mr-3 file:py-1 file:px-3 file:rounded file:border-0 file:text-xs file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200"
            />
          </div>

          {(status === "fetching" || status === "generating") && (
            <div className="border-t border-gray-100 px-6 py-4 flex items-center gap-3">
              <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-gray-600">{step}</span>
            </div>
          )}

          {status === "done" && (
            <div className="border-t border-gray-100 px-6 py-4 text-sm text-green-700">
              Newsletter downloaded successfully.
            </div>
          )}

          {status === "error" && (
            <div className="border-t border-gray-100 px-6 py-4 text-sm text-red-700">
              Error: {error}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
