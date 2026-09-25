"use client";

import React, { useState } from "react";
import type {
  ClauseItem,
  RiskLevel,
  RiskResponse,
} from "@/types";
import { RISK_BADGE_CLASS, RISK_LABELS } from "@/types";

/* ------------------------------------------------------------------ */
/* Props                                                               */
/* ------------------------------------------------------------------ */

interface RiskDashboardProps {
  /** The contract text that was submitted for analysis. */
  contractText: string;
  /** The structured risk analysis response from the backend. */
  analysis: RiskResponse;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

/** Return a colour class for the overall-risk summary bar. */
function overallRiskGradient(level: RiskLevel): string {
  const map: Record<RiskLevel, string> = {
    low: "from-emerald-600 to-emerald-400",
    medium: "from-amber-600 to-amber-400",
    high: "from-red-600 to-red-400",
    critical: "from-red-700 to-red-500",
  };
  return map[level];
}

/** Return the SVG icon for each risk level. */
function RiskIcon({ level }: { level: RiskLevel }) {
  if (level === "low") {
    return (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    );
  }
  if (level === "medium") {
    return (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
      </svg>
    );
  }
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/* Sub-components                                                      */
/* ------------------------------------------------------------------ */

/** Expandable clause card with risk details. */
function ClauseCard({ clause, index }: { clause: ClauseItem; index: number }) {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const cardId = `clause-card-${index}`;
  const contentId = `clause-content-${index}`;

  return (
    <div
      className="glass-card animate-slide-up"
      style={{ animationDelay: `${index * 80}ms`, animationFillMode: "both" }}
    >
      <button
        id={cardId}
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
        aria-controls={contentId}
        className="flex w-full items-start justify-between gap-4 p-5 text-left
                   hover:bg-white/[0.02] transition-colors duration-200"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-xs font-mono text-surface-500 uppercase tracking-wider">
              {clause.clause_type}
            </span>
            <span className={RISK_BADGE_CLASS[clause.risk_level]}>
              <RiskIcon level={clause.risk_level} />
              <span className="ml-1">{RISK_LABELS[clause.risk_level]}</span>
            </span>
          </div>
          <p className="text-sm text-surface-300 line-clamp-2 font-mono leading-relaxed">
            &ldquo;{clause.clause_text}&rdquo;
          </p>
        </div>

        {/* Expand chevron */}
        <svg
          className={`h-5 w-5 flex-shrink-0 text-surface-500 transition-transform duration-200 ${
            isExpanded ? "rotate-180" : ""
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
        </svg>
      </button>

      {/* Expandable detail panel */}
      {isExpanded && (
        <div
          id={contentId}
          role="region"
          aria-labelledby={cardId}
          className="border-t border-white/[0.06] px-5 pb-5 pt-4 animate-fade-in"
        >
          <div className="space-y-4">
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-surface-500 mb-1">
                Risk Explanation
              </h4>
              <p className="text-sm text-surface-300 leading-relaxed">
                {clause.risk_explanation}
              </p>
            </div>
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-surface-500 mb-1">
                Recommendation
              </h4>
              <p className="text-sm text-emerald-400/90 leading-relaxed">
                {clause.recommendation}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main Dashboard                                                      */
/* ------------------------------------------------------------------ */

/**
 * Side-by-side contract analysis dashboard.
 *
 * Left panel: the original contract text.
 * Right panel: AI-generated risk analysis with expandable clause cards.
 */
export default function RiskDashboard({
  contractText,
  analysis,
}: RiskDashboardProps) {
  const riskCounts: Record<RiskLevel, number> = {
    low: 0,
    medium: 0,
    high: 0,
    critical: 0,
  };

  analysis.clauses.forEach((c) => {
    riskCounts[c.risk_level]++;
  });

  return (
    <section
      aria-label="Contract risk analysis results"
      className="animate-fade-in space-y-6"
    >
      {/* ---- Overall Risk Summary Bar ---- */}
      <div
        className={`glass-card p-6 bg-gradient-to-r ${overallRiskGradient(
          analysis.overall_risk_level
        )} bg-opacity-10`}
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-white/60">
              Overall Contract Risk
            </p>
            <p className="text-2xl font-bold text-white mt-1">
              {RISK_LABELS[analysis.overall_risk_level]}
            </p>
          </div>

          {/* Risk distribution pills */}
          <div className="flex items-center gap-2 flex-wrap" aria-label="Risk distribution">
            {(Object.keys(riskCounts) as RiskLevel[]).map((level) =>
              riskCounts[level] > 0 ? (
                <span key={level} className={RISK_BADGE_CLASS[level]}>
                  {riskCounts[level]} {level}
                </span>
              ) : null
            )}
          </div>
        </div>

        <p className="mt-4 text-sm text-white/80 leading-relaxed">
          {analysis.summary}
        </p>
      </div>

      {/* ---- Side-by-side layout ---- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Original contract */}
        <div className="glass-card p-6">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-surface-400 mb-4">
            Original Contract
          </h2>
          <div
            className="max-h-[600px] overflow-y-auto pr-2 scrollbar-thin
                        text-sm text-surface-300 font-mono leading-relaxed whitespace-pre-wrap"
            tabIndex={0}
            role="document"
            aria-label="Original contract text"
          >
            {contractText}
          </div>
        </div>

        {/* Right: Clause analysis */}
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-surface-400 mb-4">
            Clause Analysis ({analysis.clauses.length} clauses)
          </h2>
          <div
            className="space-y-3 max-h-[600px] overflow-y-auto pr-1"
            role="list"
            aria-label="Analysed clauses"
          >
            {analysis.clauses.map((clause, i) => (
              <div key={i} role="listitem">
                <ClauseCard clause={clause} index={i} />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ---- Disclaimer ---- */}
      <div
        className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-5 py-4"
        role="note"
        aria-label="Legal disclaimer"
      >
        <p className="text-xs text-amber-400/80 leading-relaxed">
          ⚠️ {analysis.disclaimer}
        </p>
      </div>
    </section>
  );
}
