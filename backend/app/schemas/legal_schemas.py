"""Pydantic models for ClauseGuard AI request/response schemas.

All models use strict typing and validation. The LEGAL_DISCLAIMER constant
is hardcoded into every response to satisfy the mandatory guardrail requirement.
"""

from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    """Severity tiers for contract clause risk assessment."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Shared domain models
# ---------------------------------------------------------------------------

class ClauseItem(BaseModel):
    """A single clause extracted from a contract with its risk analysis."""

    clause_text: str = Field(
        ...,
        min_length=1,
        description="The verbatim text of the clause from the contract",
    )
    clause_type: str = Field(
        ...,
        min_length=1,
        description="Category of the clause (e.g. Termination, Liability, Indemnification)",
    )
    risk_level: RiskLevel = Field(
        ...,
        description="Assessed risk severity for this clause",
    )
    risk_explanation: str = Field(
        ...,
        min_length=1,
        description="Plain-language explanation of why this clause poses a risk",
    )
    recommendation: str = Field(
        ...,
        min_length=1,
        description="Actionable suggestion to mitigate or negotiate this clause",
    )


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class DocumentRequest(BaseModel):
    """Payload for submitting a contract for analysis."""

    contract_text: str = Field(
        ...,
        min_length=50,
        max_length=100_000,
        description="Full text content of the contract to analyse",
    )
    party_name: str = Field(
        default="",
        max_length=200,
        description="Optional — name of the party requesting analysis",
    )


# ---------------------------------------------------------------------------
# Mandatory guardrail — hardcoded into every response
# ---------------------------------------------------------------------------

LEGAL_DISCLAIMER: str = (
    "DISCLAIMER: This analysis is for informational assistance only and does not "
    "constitute formal legal advice. Please consult a qualified attorney for "
    "professional legal counsel."
)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class RiskResponse(BaseModel):
    """Structured response for contract risk analysis."""

    clauses: list[ClauseItem] = Field(
        default_factory=list,
        description="All extracted clauses with risk assessment details",
    )
    overall_risk_level: RiskLevel = Field(
        ...,
        description="Aggregate risk assessment for the entire contract",
    )
    summary: str = Field(
        ...,
        min_length=1,
        description="Executive summary of the contract analysis",
    )
    disclaimer: str = Field(
        default=LEGAL_DISCLAIMER,
        description="Mandatory legal disclaimer — always included",
    )


class PrepPackResponse(BaseModel):
    """Structured response for negotiation preparation pack."""

    key_risks: list[ClauseItem] = Field(
        default_factory=list,
        description="High-priority clauses that warrant negotiation",
    )
    negotiation_points: list[str] = Field(
        default_factory=list,
        description="Concise negotiation talking points",
    )
    alternative_language: list[str] = Field(
        default_factory=list,
        description="Suggested replacement language for risky clauses",
    )
    summary: str = Field(
        ...,
        min_length=1,
        description="Executive summary for the negotiation strategy",
    )
    disclaimer: str = Field(
        default=LEGAL_DISCLAIMER,
        description="Mandatory legal disclaimer — always included",
    )


class ErrorResponse(BaseModel):
    """Standardised error payload returned by the API."""

    detail: str = Field(..., description="Human-readable error message")
    error_code: str = Field(
        default="UNKNOWN_ERROR",
        description="Machine-readable error code for programmatic handling",
    )
