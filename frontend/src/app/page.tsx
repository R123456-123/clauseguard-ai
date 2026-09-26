"use client";

import React, { useCallback, useState } from "react";
import FileUpload from "@/components/FileUpload";
import RiskDashboard from "@/components/RiskDashboard";
import type { LegalAssistantResponse, RiskResponse } from "@/types";

/* ------------------------------------------------------------------ */
/* Constants                                                           */
/* ------------------------------------------------------------------ */

const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");
const API_REQUEST_TIMEOUT_MS = 60_000;

const SAMPLE_QUESTIONS = [
  "What are the biggest risks in this contract?",
  "What are my termination rights?",
  "Is this indemnity clause unfair to me?",
  "What should I negotiate before signing?",
];

async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit,
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(
    () => controller.abort(),
    API_REQUEST_TIMEOUT_MS,
  );

  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    window.clearTimeout(timeoutId);
  }
}

/* ------------------------------------------------------------------ */
/* Skeleton loader component                                           */
/* ------------------------------------------------------------------ */

function AnalysisSkeleton() {
  return (
    <div
      className="space-y-6 animate-fade-in"
      aria-label="Loading analysis results"
      role="status"
    >
      {/* Summary skeleton */}
      <div className="glass-card p-6 space-y-4">
        <div className="skeleton h-4 w-40 rounded" />
        <div className="skeleton h-8 w-56 rounded" />
        <div className="skeleton h-4 w-full rounded" />
        <div className="skeleton h-4 w-3/4 rounded" />
      </div>

      {/* Two-column skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card p-6 space-y-3">
          <div className="skeleton h-4 w-32 rounded" />
          {[...Array(8)].map((_, i) => (
            <div key={i} className="skeleton h-3 w-full rounded" />
          ))}
        </div>
        <div className="space-y-3">
          <div className="skeleton h-4 w-40 rounded" />
          {[...Array(4)].map((_, i) => (
            <div key={i} className="glass-card p-5 space-y-2">
              <div className="skeleton h-3 w-24 rounded" />
              <div className="skeleton h-4 w-full rounded" />
              <div className="skeleton h-3 w-2/3 rounded" />
            </div>
          ))}
        </div>
      </div>

      <p className="sr-only">Analysing your contract, please wait…</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Spinner overlay                                                     */
/* ------------------------------------------------------------------ */

function SpinnerOverlay() {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center
                  bg-surface-950/70 backdrop-blur-sm animate-fade-in"
      role="alert"
      aria-live="assertive"
    >
      <div className="flex flex-col items-center gap-4">
        <div
          className="h-12 w-12 rounded-full border-[3px] border-surface-700
                      border-t-brand-400 animate-spin"
          aria-hidden="true"
        />
        <p className="text-sm font-medium text-surface-300 animate-pulse-soft">
          Analysing contract with Gemini AI…
        </p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main page component                                                 */
/* ------------------------------------------------------------------ */

export default function HomePage() {
  const [contractText, setContractText] = useState<string>("");
  const [directInput, setDirectInput] = useState<string>("");
  const [analysis, setAnalysis] = useState<RiskResponse | null>(null);
  const [assistantAnswer, setAssistantAnswer] =
    useState<LegalAssistantResponse | null>(null);
  const [assistantQuestion, setAssistantQuestion] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const [inputMode, setInputMode] = useState<"upload" | "paste">("upload");

  /** Submit contract text to the backend for analysis. */
  const analyseContract = useCallback(async (text: string) => {
    setIsLoading(true);
    setError("");
    setAnalysis(null);
    setAssistantAnswer(null);
    setAssistantQuestion("");

    try {
      const response = await fetchWithTimeout(
        `${API_BASE}/api/v1/upload-contract`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ contract_text: text }),
        },
      );

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(
          err.detail ?? `Server responded with status ${response.status}`,
        );
      }

      const data: RiskResponse = await response.json();
      setAnalysis(data);
      setContractText(text);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "An unexpected error occurred.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  /** Handle file upload callback. */
  const handleFileText = useCallback(
    (text: string) => {
      setDirectInput(text);
      analyseContract(text);
    },
    [analyseContract],
  );

  /** Handle paste-mode submission. */
  const handlePasteSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (directInput.trim().length >= 50) {
        analyseContract(directInput);
      }
    },
    [directInput, analyseContract],
  );

  /** Ask a legal question grounded in the uploaded contract. */
  const handleAskLegalQuestion = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();
      if (!contractText.trim() || assistantQuestion.trim().length < 3) {
        return;
      }

      setIsLoading(true);
      setError("");

      try {
        const response = await fetchWithTimeout(
          `${API_BASE}/api/v1/ask-legal-question`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              ...(analysis?.document_id
                ? { document_id: analysis.document_id }
                : { contract_text: contractText }),
              question: assistantQuestion,
            }),
          },
        );

        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          throw new Error(
            err.detail ?? `Server responded with status ${response.status}`,
          );
        }

        const data: LegalAssistantResponse = await response.json();
        setAssistantAnswer(data);
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "Unable to answer your legal question.";
        setError(message);
      } finally {
        setIsLoading(false);
      }
    },
    [analysis?.document_id, assistantQuestion, contractText],
  );

  /** Reset to initial state. */
  const handleReset = useCallback(() => {
    setContractText("");
    setDirectInput("");
    setAnalysis(null);
    setAssistantAnswer(null);
    setAssistantQuestion("");
    setError("");
  }, []);

  return (
    <>
      {isLoading && <SpinnerOverlay />}

      <div className="min-h-screen">
        {/* ---- Gradient background elements ---- */}
        <div className="fixed inset-0 -z-10 overflow-hidden" aria-hidden="true">
          <div className="absolute -top-1/2 -left-1/4 h-[800px] w-[800px] rounded-full bg-brand-600/[0.07] blur-[120px]" />
          <div className="absolute -bottom-1/2 -right-1/4 h-[600px] w-[600px] rounded-full bg-cyan-500/[0.05] blur-[100px]" />
        </div>

        {/* ---- Header ---- */}
        <header className="border-b border-white/[0.06] bg-surface-950/80 backdrop-blur-lg sticky top-0 z-40">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
            <div className="flex items-center gap-3">
              <div
                className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-500/15"
                aria-hidden="true"
              >
                <svg
                  className="h-5 w-5 text-brand-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
                  />
                </svg>
              </div>
              <h1 className="text-lg font-bold tracking-tight">
                <span className="text-gradient">ClauseGuard</span>{" "}
                <span className="text-surface-400 font-normal">AI</span>
              </h1>
            </div>

            {analysis && (
              <button
                type="button"
                onClick={handleReset}
                className="rounded-lg px-4 py-2 text-sm font-medium
                           text-surface-400 hover:text-surface-200
                           hover:bg-white/[0.05] transition-colors duration-200"
                aria-label="Analyse another contract"
              >
                ← New Analysis
              </button>
            )}
          </div>
        </header>

        {/* ---- Main content ---- */}
        <main className="mx-auto max-w-7xl px-6 py-10" aria-busy={isLoading}>
          {!analysis && !isLoading && (
            <div className="mx-auto max-w-2xl animate-fade-in">
              {/* Hero */}
              <div className="text-center mb-10">
                <h2 className="text-4xl sm:text-5xl font-extrabold tracking-tight mb-4">
                  Understand your legal documents{" "}
                  <span className="text-gradient">before you sign</span>
                </h2>
                <p className="text-lg text-surface-400 leading-relaxed max-w-xl mx-auto">
                  Upload a contract and ask practical legal questions.
                  ClauseGuard AI explains risky clauses, highlights obligations,
                  and helps you prepare for a smarter review.
                </p>
              </div>

              {/* Input mode tabs */}
              <div
                className="flex items-center justify-center gap-1 mb-8
                            rounded-xl bg-surface-900/60 p-1 max-w-xs mx-auto"
                role="tablist"
                aria-label="Input method selection"
              >
                <button
                  role="tab"
                  type="button"
                  id="tab-upload"
                  aria-selected={inputMode === "upload"}
                  aria-controls="panel-upload"
                  onClick={() => setInputMode("upload")}
                  className={`flex-1 rounded-lg px-4 py-2 text-sm font-medium
                              transition-all duration-200
                              ${
                                inputMode === "upload"
                                  ? "bg-brand-500/20 text-brand-300 shadow-sm"
                                  : "text-surface-400 hover:text-surface-300"
                              }`}
                >
                  Upload File
                </button>
                <button
                  role="tab"
                  type="button"
                  id="tab-paste"
                  aria-selected={inputMode === "paste"}
                  aria-controls="panel-paste"
                  onClick={() => setInputMode("paste")}
                  className={`flex-1 rounded-lg px-4 py-2 text-sm font-medium
                              transition-all duration-200
                              ${
                                inputMode === "paste"
                                  ? "bg-brand-500/20 text-brand-300 shadow-sm"
                                  : "text-surface-400 hover:text-surface-300"
                              }`}
                >
                  Paste Text
                </button>
              </div>

              {/* Upload panel */}
              {inputMode === "upload" && (
                <div
                  id="panel-upload"
                  role="tabpanel"
                  aria-labelledby="tab-upload"
                  className="animate-fade-in"
                >
                  <FileUpload
                    onTextExtracted={handleFileText}
                    isLoading={isLoading}
                  />
                </div>
              )}

              {/* Paste panel */}
              {inputMode === "paste" && (
                <div
                  id="panel-paste"
                  role="tabpanel"
                  aria-labelledby="tab-paste"
                  className="animate-fade-in"
                >
                  <form onSubmit={handlePasteSubmit}>
                    <label
                      htmlFor="contract-text-input"
                      className="block text-sm font-medium text-surface-400 mb-2"
                    >
                      Paste your contract text below
                    </label>
                    <textarea
                      id="contract-text-input"
                      value={directInput}
                      onChange={(e) => setDirectInput(e.target.value)}
                      placeholder="Paste the full text of your contract here (minimum 50 characters)…"
                      rows={12}
                      className="w-full rounded-2xl border border-white/[0.06] bg-white/[0.03]
                                 backdrop-blur-md px-5 py-4 text-sm text-surface-200
                                 font-mono leading-relaxed placeholder:text-surface-600
                                 focus:border-brand-500/40 focus:ring-2 focus:ring-brand-500/20
                                 transition-all duration-200 resize-y"
                      aria-describedby="paste-instructions"
                      disabled={isLoading}
                    />
                    <p
                      id="paste-instructions"
                      className="mt-2 text-xs text-surface-500"
                    >
                      {directInput.length}/100,000 characters
                      {directInput.length > 0 && directInput.length < 50 && (
                        <span className="text-amber-400 ml-2">
                          — need at least 50 characters
                        </span>
                      )}
                      {directInput.length > 100000 && (
                        <span className="text-red-400 ml-2">
                          — maximum length exceeded
                        </span>
                      )}
                    </p>

                    <button
                      type="submit"
                      disabled={
                        isLoading ||
                        directInput.trim().length < 50 ||
                        directInput.length > 100000
                      }
                      className="btn-primary mt-4 w-full"
                      aria-label="Analyse pasted contract"
                    >
                      <svg
                        className="h-5 w-5"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                        aria-hidden="true"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5"
                        />
                      </svg>
                      Analyse Contract
                    </button>
                  </form>
                </div>
              )}

              {/* Error display */}
              {error && (
                <div
                  className="mt-6 rounded-xl border border-red-500/20 bg-red-500/5 px-5 py-4 animate-fade-in"
                  role="alert"
                  aria-live="assertive"
                >
                  <div className="flex items-start gap-3">
                    <svg
                      className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
                      />
                    </svg>
                    <div>
                      <p className="text-sm font-medium text-red-400">
                        Analysis Failed
                      </p>
                      <p className="mt-1 text-sm text-red-400/70">{error}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Loading skeleton */}
          {isLoading && <AnalysisSkeleton />}

          {/* Results dashboard */}
          {analysis && !isLoading && (
            <>
              <RiskDashboard contractText={contractText} analysis={analysis} />

              <div className="mt-8 glass-card p-6 animate-fade-in">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-surface-400">
                      Legal document assistant
                    </p>
                    <h3 className="mt-1 text-xl font-bold text-white">
                      Ask a question about this contract
                    </h3>
                  </div>
                </div>

                <form
                  onSubmit={handleAskLegalQuestion}
                  className="mt-5 space-y-4"
                >
                  <div className="flex flex-wrap gap-2">
                    {SAMPLE_QUESTIONS.map((sample) => (
                      <button
                        key={sample}
                        type="button"
                        onClick={() => setAssistantQuestion(sample)}
                        className="rounded-full border border-brand-500/20 bg-brand-500/5 px-3 py-1.5 text-xs text-brand-200 transition hover:border-brand-400/40 hover:bg-brand-500/10"
                      >
                        {sample}
                      </button>
                    ))}
                  </div>

                  <label htmlFor="legal-question-input" className="sr-only">
                    Ask a legal question about the contract
                  </label>
                  <textarea
                    id="legal-question-input"
                    value={assistantQuestion}
                    onChange={(e) => setAssistantQuestion(e.target.value)}
                    rows={4}
                    placeholder="Examples: What are my termination rights? Is this indemnity clause risky? What should I negotiate before signing?"
                    className="w-full rounded-2xl border border-white/[0.06] bg-white/[0.03] px-4 py-3 text-sm text-surface-200 placeholder:text-surface-600 focus:border-brand-500/40 focus:ring-2 focus:ring-brand-500/20 transition-all duration-200 resize-y"
                  />

                  <div className="flex items-center justify-between gap-3">
                    <p className="text-xs text-surface-500">
                      Informational support only — not legal advice.
                    </p>
                    <button
                      type="submit"
                      disabled={
                        isLoading || assistantQuestion.trim().length < 3
                      }
                      className="btn-primary"
                    >
                      Ask question
                    </button>
                  </div>
                </form>

                {assistantAnswer && (
                  <div className="mt-6 rounded-2xl border border-brand-500/20 bg-brand-500/5 p-5">
                    <p className="text-xs font-semibold uppercase tracking-wider text-brand-300">
                      Answer
                    </p>
                    <p className="mt-3 text-sm leading-relaxed text-surface-200">
                      {assistantAnswer.answer}
                    </p>

                    {assistantAnswer.key_points.length > 0 && (
                      <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-surface-300">
                        {assistantAnswer.key_points.map((point, index) => (
                          <li key={index}>{point}</li>
                        ))}
                      </ul>
                    )}

                    <p className="mt-4 text-xs text-amber-300/80">
                      ⚠️ {assistantAnswer.disclaimer}
                    </p>
                  </div>
                )}
              </div>
            </>
          )}
        </main>

        {/* ---- Footer ---- */}
        <footer className="border-t border-white/[0.06] mt-16">
          <div className="mx-auto max-w-7xl px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-xs text-surface-500">
              © {new Date().getFullYear()} ClauseGuard AI — For informational
              purposes only
            </p>
            <p className="text-xs text-surface-600">
              Powered by Google Gemini AI
            </p>
          </div>
        </footer>
      </div>
    </>
  );
}
