"""API route definitions for ClauseGuard AI.

Exposes POST endpoints for contract analysis, negotiation prep-pack generation,
and contract-grounded legal questions. Each returns a structured Pydantic
response with a mandatory legal disclaimer.
"""

import logging

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
from app.services.context_cache import get as get_cached_context

router: APIRouter = APIRouter(tags=["contracts"])
logger = logging.getLogger(__name__)


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
        logger.warning("Contract analysis service failure: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="The contract analysis service is temporarily unavailable.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected contract analysis failure")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during contract analysis.",
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
        logger.warning("Prep-pack service failure: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="The preparation service is temporarily unavailable.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected prep-pack failure")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during preparation generation.",
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
        contract_text = request.contract_text
        if request.document_id:
            contract_text = get_cached_context(request.document_id)
            if contract_text is None:
                raise HTTPException(
                    status_code=410,
                    detail="The cached contract context has expired. Please analyse the contract again.",
                )
        return await answer_legal_question(contract_text or "", request.question)
    except HTTPException:
        raise
    except GeminiServiceError as exc:
        logger.warning("Legal assistant service failure: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="The legal assistant service is temporarily unavailable.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected legal assistant failure")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while answering the question.",
        ) from exc
