/**
 * Shared TypeScript interfaces for ClauseGuard AI frontend.
 *
 * These mirror the Pydantic schemas in the backend to guarantee
 * type-safe data flow across the API boundary.
 */

/** Risk severity levels — must match backend `RiskLevel` enum values. */
export type RiskLevel = "low" | "medium" | "high" | "critical";

/** A single clause extracted from a contract with its risk analysis. */
export interface ClauseItem {
  clause_text: string;
  clause_type: string;
  risk_level: RiskLevel;
  risk_explanation: string;
  recommendation: string;
}

/** Response from the `/upload-contract` endpoint. */
export interface RiskResponse {
  clauses: ClauseItem[];
  overall_risk_level: RiskLevel;
  summary: string;
  disclaimer: string;
}

/** Response from the `/generate-prep-pack` endpoint. */
export interface PrepPackResponse {
  key_risks: ClauseItem[];
  negotiation_points: string[];
  alternative_language: string[];
  summary: string;
  disclaimer: string;
}

export interface LegalAssistantResponse {
  answer: string;
  key_points: string[];
  disclaimer: string;
}

/** Request payload sent to both endpoints. */
export interface DocumentRequest {
  contract_text: string;
  party_name?: string;
}

export interface LegalAssistantRequest {
  contract_text: string;
  question: string;
}

/** Maps risk levels to human-readable labels. */
export const RISK_LABELS: Record<RiskLevel, string> = {
  low: "Low Risk",
  medium: "Medium Risk",
  high: "High Risk",
  critical: "Critical Risk",
};

/** Maps risk levels to Tailwind badge class names. */
export const RISK_BADGE_CLASS: Record<RiskLevel, string> = {
  low: "badge-low",
  medium: "badge-medium",
  high: "badge-high",
  critical: "badge-critical",
};
