"""API route definitions for ClauseGuard AI.

Exposes two POST endpoints for contract analysis and negotiation prep-pack
generation, both returning structured Pydantic responses with mandatory
legal disclaimers.
"""

from fastapi import APIRouter, HTTPException

from app.schemas.legal_schemas import (
    DocumentRequest,
    ErrorResponse,
    LegalAssistantRequest,
    LegalAssistantResponse,
    PrepPackResponse,
    RiskResponse,
)
from app.services.gemini_service import (
    GeminiServiceError,
    analyze_contract,
    answer_legal_question,
    generate_prep_pack,
)

router: APIRouter = APIRouter(tags=["contracts"])


@router.post(
    "/upload-contract",
    response_model=RiskResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "AI service failure"},
    },
    summary="Analyse a contract for legal risks",
    description=(
        "Accepts contract text, scrubs PII, sends to Gemini AI for clause-level "
        "risk analysis, and returns a structured risk report with a mandatory "
        "legal disclaimer."
    ),
)
async def upload_contract(request: DocumentRequest) -> RiskResponse:
    """Analyse a contract document for legal risks."""
    try:
        return await analyze_contract(request.contract_text)
    except GeminiServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during contract analysis: {exc}",
        ) from exc


@router.post(
    "/generate-prep-pack",
    response_model=PrepPackResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "AI service failure"},
    },
    summary="Generate a negotiation preparation pack",
    description=(
        "Analyses contract text and produces a negotiation prep pack including "
        "key risk highlights, talking points, and suggested alternative language."
    ),
)
async def generate_preparation_pack(
    request: DocumentRequest,
) -> PrepPackResponse:
    """Generate a negotiation preparation pack for a contract."""
    try:
        return await generate_prep_pack(request.contract_text)
    except GeminiServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during prep-pack generation: {exc}",
        ) from exc


@router.post(
    "/ask-legal-question",
    response_model=LegalAssistantResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "AI service failure"},
    },
    summary="Answer a legal question about a contract",
    description=(
        "Uses the uploaded contract text as context and answers the user's legal "
        "question in plain English while staying within informational guidance."
    ),
)
async def ask_legal_question(
    request: LegalAssistantRequest,
) -> LegalAssistantResponse:
    """Answer a user question grounded in their contract text."""
    try:
        return await answer_legal_question(request.contract_text, request.question)
    except GeminiServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during legal question answering: {exc}",
        ) from exc
