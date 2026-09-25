"""Google Gemini AI Service — contract analysis and prep-pack generation.

All outbound text is scrubbed of PII before hitting the Gemini API.
Responses are requested as structured JSON and validated through Pydantic.
"""

from __future__ import annotations

import json
import os
from typing import Any

import google.generativeai as genai
from dotenv import load_dotenv

from app.schemas.legal_schemas import (
    LEGAL_DISCLAIMER,
    ClauseItem,
    PrepPackResponse,
    RiskLevel,
    RiskResponse,
)
from app.services.pii_scrubber import scrub_pii

load_dotenv()


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class GeminiServiceError(Exception):
    """Raised when the Gemini API call or response parsing fails."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

import functools

@functools.lru_cache(maxsize=1)
def _get_model() -> genai.GenerativeModel:
    """Configure the Gemini client and return a ``GenerativeModel`` instance.

    Raises:
        GeminiServiceError: If ``GEMINI_API_KEY`` is not set.
    """
    api_key: str | None = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiServiceError(
            "GEMINI_API_KEY environment variable is not set. "
            "Please add it to your .env file."
        )

    genai.configure(api_key=api_key)

    return genai.GenerativeModel(
        model_name="gemini-3.5-flash",
        generation_config=genai.GenerationConfig(
            temperature=0.2,
            top_p=0.8,
            response_mime_type="application/json",
        ),
    )


def _build_analysis_prompt(contract_text: str) -> str:
    """Return the structured prompt for full contract risk analysis."""
    return (
        "You are a legal contract risk analysis expert. "
        "Analyse the following contract text and extract every notable clause "
        "with its associated risk.\n\n"
        "Return your analysis as a JSON object with this exact structure:\n"
        "{\n"
        '  "clauses": [\n'
        "    {\n"
        '      "clause_text": "exact text of the clause",\n'
        '      "clause_type": "Termination | Liability | Indemnification | '
        "Confidentiality | Payment | IP Rights | Non-Compete | Data Privacy | "
        'Governing Law | Force Majeure | Other",\n'
        '      "risk_level": "low | medium | high | critical",\n'
        '      "risk_explanation": "why this clause poses a risk",\n'
        '      "recommendation": "suggested action or modification"\n'
        "    }\n"
        "  ],\n"
        '  "overall_risk_level": "low | medium | high | critical",\n'
        '  "summary": "executive summary in 2-3 sentences"\n'
        "}\n\n"
        "CONTRACT TEXT:\n"
        f"{contract_text}\n\n"
        "Be thorough — analyse every significant clause."
    )


def _build_prep_pack_prompt(contract_text: str) -> str:
    """Return the structured prompt for negotiation preparation."""
    return (
        "You are a legal negotiation preparation expert. "
        "Analyse the following contract and produce a negotiation preparation pack.\n\n"
        "Return your analysis as a JSON object with this exact structure:\n"
        "{\n"
        '  "key_risks": [\n'
        "    {\n"
        '      "clause_text": "exact text of the risky clause",\n'
        '      "clause_type": "category of the clause",\n'
        '      "risk_level": "low | medium | high | critical",\n'
        '      "risk_explanation": "why this is a negotiation concern",\n'
        '      "recommendation": "specific negotiation strategy"\n'
        "    }\n"
        "  ],\n"
        '  "negotiation_points": ["point 1", "point 2"],\n'
        '  "alternative_language": ["suggested replacement clause 1"],\n'
        '  "summary": "executive summary for negotiation in 2-3 sentences"\n'
        "}\n\n"
        "CONTRACT TEXT:\n"
        f"{contract_text}\n\n"
        "Focus on the most negotiable and highest-risk clauses."
    )


def _parse_json_response(raw_text: str) -> dict[str, Any]:
    """Parse the Gemini response text into a Python dict.

    Raises:
        GeminiServiceError: If the text is not valid JSON.
    """
    try:
        data: dict[str, Any] = json.loads(raw_text)
        return data
    except json.JSONDecodeError as exc:
        raise GeminiServiceError(
            f"Gemini returned non-JSON output: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def analyze_contract(contract_text: str) -> RiskResponse:
    """Analyse a contract for risks using Google Gemini AI.

    Pipeline:
        1. Scrub PII from the input text.
        2. Send the sanitised text to Gemini with a structured JSON prompt.
        3. Parse and validate the response via Pydantic models.

    Args:
        contract_text: Raw contract text (may contain PII).

    Returns:
        A fully validated ``RiskResponse`` with the mandatory disclaimer.

    Raises:
        GeminiServiceError: On API or parsing failures.
    """
    # 1 — PII scrubbing
    scrub_result = scrub_pii(contract_text)

    # 2 — Gemini API call
    model = _get_model()
    prompt = _build_analysis_prompt(scrub_result.cleaned_text)

    try:
        response = await model.generate_content_async(prompt)
        raw_data = _parse_json_response(response.text)
    except GeminiServiceError:
        raise
    except Exception as exc:
        raise GeminiServiceError(f"Gemini API call failed: {exc}") from exc

    # 3 — Validate into Pydantic models
    clauses: list[ClauseItem] = [
        ClauseItem(**item) for item in raw_data.get("clauses", [])
    ]

    return RiskResponse(
        clauses=clauses,
        overall_risk_level=RiskLevel(raw_data.get("overall_risk_level", "medium")),
        summary=raw_data.get("summary", "Analysis complete."),
        disclaimer=LEGAL_DISCLAIMER,
    )


async def generate_prep_pack(contract_text: str) -> PrepPackResponse:
    """Generate a negotiation preparation pack using Google Gemini AI.

    Args:
        contract_text: Raw contract text (may contain PII).

    Returns:
        A fully validated ``PrepPackResponse`` with the mandatory disclaimer.

    Raises:
        GeminiServiceError: On API or parsing failures.
    """
    scrub_result = scrub_pii(contract_text)

    model = _get_model()
    prompt = _build_prep_pack_prompt(scrub_result.cleaned_text)

    try:
        response = await model.generate_content_async(prompt)
        raw_data = _parse_json_response(response.text)
    except GeminiServiceError:
        raise
    except Exception as exc:
        raise GeminiServiceError(f"Gemini API call failed: {exc}") from exc

    key_risks: list[ClauseItem] = [
        ClauseItem(**item) for item in raw_data.get("key_risks", [])
    ]

    return PrepPackResponse(
        key_risks=key_risks,
        negotiation_points=raw_data.get("negotiation_points", []),
        alternative_language=raw_data.get("alternative_language", []),
        summary=raw_data.get("summary", "Preparation pack generated."),
        disclaimer=LEGAL_DISCLAIMER,
    )
