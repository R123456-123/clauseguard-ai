"""Google Gemini AI Service — contract analysis and prep-pack generation.

All outbound text is scrubbed of PII before hitting the Gemini API.
Responses are requested as structured JSON and validated through Pydantic.
"""

from __future__ import annotations

import json
import os
import asyncio
import functools
from typing import Any, TypeVar

import google.generativeai as genai
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

from app.schemas.legal_schemas import (
    GeminiAssistantResponse,
    GeminiPrepPackResponse,
    GeminiRiskResponse,
    LEGAL_DISCLAIMER,
    LegalAssistantResponse,
    PrepPackResponse,
    RiskResponse,
)
from app.services.pii_scrubber import scrub_pii
from app.services.context_cache import store

load_dotenv()


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class GeminiServiceError(Exception):
    """Raised when the Gemini API call or response parsing fails."""


_GEMINI_TIMEOUT_SECONDS = 45
ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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


def _build_legal_question_prompt(contract_text: str, question: str) -> str:
    """Return the structured prompt for contract-grounded legal Q&A."""
    return (
        "You are a careful legal document assistant. Answer the user's question using the "
        "provided contract text as the main source of truth. Do not invent terms, rights, "
        "or obligations that are not in the contract. Keep the answer practical and plain-English, "
        "and explain the legal impact clearly.\n\n"
        "Return your answer as JSON with this exact structure:\n"
        "{\n"
        '  "answer": "clear response in 2-5 sentences",\n'
        '  "key_points": ["main takeaway 1", "main takeaway 2"]\n'
        "}\n\n"
        "USER QUESTION:\n"
        f"{question}\n\n"
        "CONTRACT TEXT:\n"
        f"{contract_text}\n\n"
        "If the contract is unclear or incomplete, say so briefly and suggest what a user may want to verify with a lawyer."
    )


def _parse_json_response(raw_text: str) -> dict[str, Any]:
    """Parse the Gemini response text into a Python dict.

    Raises:
        GeminiServiceError: If the text is not valid JSON.
    """
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise GeminiServiceError(
            f"Gemini returned non-JSON output: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise GeminiServiceError("Gemini returned JSON in an unsupported format.")

    return data


def _validate_response(
    response_model: type[ResponseModel],
    data: dict[str, Any],
) -> ResponseModel:
    """Validate the complete Gemini payload before mapping it to an API response."""
    try:
        return response_model.model_validate(data)
    except ValidationError as exc:
        raise GeminiServiceError(
            "Gemini returned incomplete or invalid structured data."
        ) from exc


async def _generate_json(prompt: str) -> dict[str, Any]:
    """Generate one bounded, structured response from Gemini."""
    try:
        response = await asyncio.wait_for(
            _get_model().generate_content_async(prompt),
            timeout=_GEMINI_TIMEOUT_SECONDS,
        )
        return _parse_json_response(response.text)
    except asyncio.TimeoutError as exc:
        raise GeminiServiceError("Gemini request timed out.") from exc
    except GeminiServiceError:
        raise
    except Exception as exc:
        raise GeminiServiceError(f"Gemini API call failed: {exc}") from exc


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
    document_id = store(scrub_result.cleaned_text)

    # 2 — Gemini API call
    prompt = _build_analysis_prompt(scrub_result.cleaned_text)
    raw_data = _validate_response(
        GeminiRiskResponse,
        await _generate_json(prompt),
    )

    return RiskResponse(
        clauses=raw_data.clauses,
        overall_risk_level=raw_data.overall_risk_level,
        summary=raw_data.summary,
        disclaimer=LEGAL_DISCLAIMER,
        document_id=document_id,
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

    prompt = _build_prep_pack_prompt(scrub_result.cleaned_text)
    raw_data = _validate_response(
        GeminiPrepPackResponse,
        await _generate_json(prompt),
    )

    return PrepPackResponse(
        key_risks=raw_data.key_risks,
        negotiation_points=raw_data.negotiation_points,
        alternative_language=raw_data.alternative_language,
        summary=raw_data.summary,
        disclaimer=LEGAL_DISCLAIMER,
    )


async def answer_legal_question(
    contract_text: str,
    question: str,
) -> LegalAssistantResponse:
    """Answer a user's legal question grounded in the contract text."""
    scrub_result = scrub_pii(contract_text)

    prompt = _build_legal_question_prompt(scrub_result.cleaned_text, question)
    raw_data = _validate_response(
        GeminiAssistantResponse,
        await _generate_json(prompt),
    )

    return LegalAssistantResponse(
        answer=raw_data.answer,
        key_points=raw_data.key_points,
        disclaimer=LEGAL_DISCLAIMER,
    )
