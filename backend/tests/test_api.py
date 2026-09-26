"""Tests for ClauseGuard AI API endpoints and PII scrubbing logic.

Uses FastAPI's TestClient for synchronous endpoint testing and
directly tests the PII scrubber as a unit.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.legal_schemas import (
    LEGAL_DISCLAIMER,
    ClauseItem,
    LegalAssistantResponse,
    PrepPackResponse,
    RiskLevel,
    RiskResponse,
)
from app.services.pii_scrubber import scrub_pii
from app.services.context_cache import clear as clear_context_cache, get as get_cached_context, store
from app.services.gemini_service import (
    GeminiServiceError,
    _parse_json_response,
    _validate_response,
    analyze_contract,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

client = TestClient(app)

_SAMPLE_CONTRACT: str = (
    "This Service Agreement is entered into by ACME Corp and Jane Doe. "
    "The Contractor agrees to a non-compete clause lasting 5 years within "
    "a 200-mile radius. Termination may occur with 7 days written notice. "
    "Liability is capped at $500. Governing law shall be the State of Delaware."
)

_MOCK_RISK_RESPONSE = RiskResponse(
    clauses=[
        ClauseItem(
            clause_text="non-compete clause lasting 5 years within a 200-mile radius",
            clause_type="Non-Compete",
            risk_level=RiskLevel.HIGH,
            risk_explanation="A 5-year, 200-mile non-compete is unusually broad and may be unenforceable.",
            recommendation="Negotiate to reduce the duration to 1-2 years and the radius to 50 miles.",
        ),
        ClauseItem(
            clause_text="Termination may occur with 7 days written notice",
            clause_type="Termination",
            risk_level=RiskLevel.MEDIUM,
            risk_explanation="7-day termination notice is very short for a service agreement.",
            recommendation="Request a minimum 30-day notice period for both parties.",
        ),
    ],
    overall_risk_level=RiskLevel.HIGH,
    summary="The contract contains a highly restrictive non-compete and short termination window.",
    disclaimer=LEGAL_DISCLAIMER,
)


# ===========================================================================
# 1. Health check endpoint
# ===========================================================================


class TestHealthCheck:
    """Verify the liveness probe endpoint works correctly."""

    def test_health_returns_200(self) -> None:
        """GET /health should return 200 with status=healthy."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "clauseguard-ai"


# ===========================================================================
# 2. PII Scrubbing unit tests
# ===========================================================================


class TestPIIScrubber:
    """Unit tests for the regex-based PII scrubber."""

    def test_scrubs_email_addresses(self) -> None:
        """Email addresses should be replaced with [EMAIL_REDACTED]."""
        text = "Contact john.doe@example.com for details."
        result = scrub_pii(text)

        assert "[EMAIL_REDACTED]" in result.cleaned_text
        assert "john.doe@example.com" not in result.cleaned_text
        assert result.redaction_count == 1

    def test_scrubs_phone_numbers(self) -> None:
        """US phone numbers should be replaced with [PHONE_REDACTED]."""
        text = "Call us at (555) 123-4567 or +1-800-555-0199."
        result = scrub_pii(text)

        assert "[PHONE_REDACTED]" in result.cleaned_text
        assert "(555) 123-4567" not in result.cleaned_text
        assert result.redaction_count >= 2

    def test_scrubs_ssn_format(self) -> None:
        """SSN-format numbers should be replaced with [SSN_REDACTED]."""
        text = "SSN: 123-45-6789 is on file."
        result = scrub_pii(text)

        assert "[SSN_REDACTED]" in result.cleaned_text
        assert "123-45-6789" not in result.cleaned_text


class TestContextCache:
    """Verify scrubbed contract context is bounded and expires by ID."""

    def setup_method(self) -> None:
        clear_context_cache()

    def teardown_method(self) -> None:
        clear_context_cache()

    def test_round_trips_scrubbed_context(self) -> None:
        """A stored context should be retrievable without storing raw PII."""
        document_id = store("Agreement with [EMAIL_REDACTED]")

        assert len(document_id) == 24
        assert get_cached_context(document_id) == "Agreement with [EMAIL_REDACTED]"
        assert get_cached_context("invalid-document-id") is None

    def test_scrubs_multiple_pii_types(self) -> None:
        """Multiple PII types in one text should all be redacted."""
        text = (
            "Contact jane@corp.com or call 555-111-2222. "
            "SSN on file: 999-88-7777."
        )
        result = scrub_pii(text)

        assert "jane@corp.com" not in result.cleaned_text
        assert "555-111-2222" not in result.cleaned_text
        assert "999-88-7777" not in result.cleaned_text
        assert result.redaction_count >= 3

    def test_no_pii_returns_unchanged(self) -> None:
        """Text without PII should pass through unchanged."""
        text = "This agreement is governed by Delaware law."
        result = scrub_pii(text)

        assert result.cleaned_text == text
        assert result.redaction_count == 0

    def test_redaction_count_matches_replacements(self) -> None:
        """Each supported PII occurrence should increment the count once."""
        result = scrub_pii("a@example.com, b@example.com, 123-45-6789")

        assert result.redaction_count == 3
        assert "@example.com" not in result.cleaned_text
        assert "123-45-6789" not in result.cleaned_text


# ===========================================================================
# 2b. Structured AI response validation
# ===========================================================================


class TestGeminiResponseValidation:
    """Verify malformed model output is rejected before reaching the API."""

    def test_rejects_non_object_json(self) -> None:
        """A JSON array is not a valid top-level Gemini response."""
        with pytest.raises(GeminiServiceError, match="unsupported format"):
            _parse_json_response("[]")

    def test_rejects_invalid_json(self) -> None:
        """Malformed JSON should become the service's controlled error type."""
        with pytest.raises(GeminiServiceError, match="non-JSON"):
            _parse_json_response("not-json")

    def test_rejects_incomplete_risk_response(self) -> None:
        """Required risk fields must be present in model output."""
        with pytest.raises(GeminiServiceError, match="incomplete"):
            _validate_response(
                RiskResponse,
                {"clauses": [], "overall_risk_level": "high"},
            )

    @patch(
        "app.services.gemini_service._generate_json",
        new_callable=AsyncMock,
        return_value={
            "clauses": [],
            "overall_risk_level": "low",
            "summary": "No significant risks found.",
        },
    )
    def test_service_scrubs_pii_before_prompt_generation(
        self,
        mock_generate: AsyncMock,
    ) -> None:
        """The service should never send raw email or SSN data to Gemini."""
        contract = f"This agreement is valid. Contact jane@example.com. SSN 123-45-6789."

        result = asyncio.run(analyze_contract(contract))

        assert result.overall_risk_level == RiskLevel.LOW
        prompt = mock_generate.call_args.args[0]
        assert "jane@example.com" not in prompt
        assert "123-45-6789" not in prompt
        assert "[EMAIL_REDACTED]" in prompt
        assert "[SSN_REDACTED]" in prompt


# ===========================================================================
# 3. Contract analysis endpoint
# ===========================================================================


class TestUploadContract:
    """Integration tests for POST /api/v1/upload-contract."""

    @patch(
        "app.api.routes.analyze_contract",
        new_callable=AsyncMock,
        return_value=_MOCK_RISK_RESPONSE,
    )
    def test_successful_analysis(self, mock_analyze: AsyncMock) -> None:
        """A valid contract should return 200 with clause analysis."""
        response = client.post(
            "/api/v1/upload-contract",
            json={"contract_text": _SAMPLE_CONTRACT},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "clauses" in data
        assert "overall_risk_level" in data
        assert "summary" in data
        assert "disclaimer" in data

        # Verify mandatory disclaimer is always present
        assert data["disclaimer"] == LEGAL_DISCLAIMER

        # Verify clauses are populated
        assert len(data["clauses"]) == 2
        assert data["clauses"][0]["risk_level"] == "high"
        assert data["overall_risk_level"] == "high"

        # Verify the service was called
        mock_analyze.assert_called_once_with(_SAMPLE_CONTRACT)

    def test_rejects_short_contract(self) -> None:
        """Contract text shorter than 50 chars should return 422."""
        response = client.post(
            "/api/v1/upload-contract",
            json={"contract_text": "Too short."},
        )

        assert response.status_code == 422

    def test_rejects_missing_contract_text(self) -> None:
        """Missing contract_text field should return 422."""
        response = client.post(
            "/api/v1/upload-contract",
            json={},
        )

        assert response.status_code == 422

    @patch(
        "app.api.routes.analyze_contract",
        new_callable=AsyncMock,
        side_effect=Exception("Gemini API timeout"),
    )
    def test_handles_service_failure(self, mock_analyze: AsyncMock) -> None:
        """Service failures should return 500 with an error message."""
        response = client.post(
            "/api/v1/upload-contract",
            json={"contract_text": _SAMPLE_CONTRACT},
        )

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    @patch(
        "app.api.routes.analyze_contract",
        new_callable=AsyncMock,
        side_effect=GeminiServiceError("provider secret should not leak"),
    )
    def test_hides_provider_error_details(self, mock_analyze: AsyncMock) -> None:
        """Provider failures should return a safe message and gateway status."""
        response = client.post(
            "/api/v1/upload-contract",
            json={"contract_text": _SAMPLE_CONTRACT},
        )

        assert response.status_code == 502
        assert response.json()["detail"] == (
            "The contract analysis service is temporarily unavailable."
        )
        assert "provider secret" not in response.text


# ===========================================================================
# 4. Prep-pack endpoint
# ===========================================================================

_MOCK_PREP_PACK = PrepPackResponse(
    key_risks=[
        ClauseItem(
            clause_text="Termination may occur with 7 days written notice",
            clause_type="Termination",
            risk_level=RiskLevel.MEDIUM,
            risk_explanation="7-day termination notice is very short.",
            recommendation="Request a minimum 30-day notice period.",
        ),
    ],
    negotiation_points=["Extend termination notice", "Cap liability"],
    alternative_language=["Either party may terminate with 30 days written notice."],
    summary="Focus on extending the termination window.",
    disclaimer=LEGAL_DISCLAIMER,
)

_MOCK_LEGAL_ASSISTANT_RESPONSE = LegalAssistantResponse(
    answer="The contract allows termination with 7 days' notice and includes a broad non-compete. This creates a risk for your operational flexibility.",
    key_points=[
        "Termination can happen with 7 days' notice.",
        "The non-compete lasts five years within a 200-mile radius.",
    ],
    disclaimer=LEGAL_DISCLAIMER,
)


class TestGeneratePrepPack:
    """Integration tests for POST /api/v1/generate-prep-pack."""

    @patch(
        "app.api.routes.generate_prep_pack",
        new_callable=AsyncMock,
        return_value=_MOCK_PREP_PACK,
    )
    def test_successful_prep_pack(self, mock_generate: AsyncMock) -> None:
        """A valid contract should return a prep pack."""
        response = client.post(
            "/api/v1/generate-prep-pack",
            json={"contract_text": _SAMPLE_CONTRACT},
        )
        assert response.status_code == 200
        data = response.json()
        assert "negotiation_points" in data
        assert "alternative_language" in data
        assert data["disclaimer"] == LEGAL_DISCLAIMER
        mock_generate.assert_called_once_with(_SAMPLE_CONTRACT)

    def test_rejects_short_contract(self) -> None:
        """Contract text shorter than 50 chars should return 422."""
        response = client.post(
            "/api/v1/generate-prep-pack",
            json={"contract_text": "Short."},
        )
        assert response.status_code == 422

    @patch(
        "app.api.routes.generate_prep_pack",
        new_callable=AsyncMock,
        side_effect=Exception("API Error"),
    )
    def test_handles_service_failure(self, mock_generate: AsyncMock) -> None:
        """Service failures should return 500."""
        response = client.post(
            "/api/v1/generate-prep-pack",
            json={"contract_text": _SAMPLE_CONTRACT},
        )
        assert response.status_code == 500


class TestAskLegalQuestion:
    """Integration tests for POST /api/v1/ask-legal-question."""

    @patch(
        "app.api.routes.answer_legal_question",
        new_callable=AsyncMock,
        return_value=_MOCK_LEGAL_ASSISTANT_RESPONSE,
    )
    def test_successful_question_answer(self, mock_answer: AsyncMock) -> None:
        """Valid question requests should return a grounded legal answer."""
        response = client.post(
            "/api/v1/ask-legal-question",
            json={
                "contract_text": _SAMPLE_CONTRACT,
                "question": "What are the biggest risks in this contract?",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "key_points" in data
        assert data["disclaimer"] == LEGAL_DISCLAIMER
        mock_answer.assert_called_once_with(
            _SAMPLE_CONTRACT,
            "What are the biggest risks in this contract?",
        )

    def test_rejects_missing_question(self) -> None:
        """Missing questions should return 422 validation error."""
        response = client.post(
            "/api/v1/ask-legal-question",
            json={"contract_text": _SAMPLE_CONTRACT},
        )

        assert response.status_code == 422

    def test_rejects_question_over_limit(self) -> None:
        """Very large questions should be rejected before an AI request."""
        response = client.post(
            "/api/v1/ask-legal-question",
            json={
                "contract_text": _SAMPLE_CONTRACT,
                "question": "x" * 2001,
            },
        )

        assert response.status_code == 422

    def test_expired_document_id_uses_text_fallback(self) -> None:
        """An expired ID should fall back to the supplied contract text."""
        with patch(
            "app.api.routes.answer_legal_question",
            new_callable=AsyncMock,
            return_value=_MOCK_LEGAL_ASSISTANT_RESPONSE,
        ) as mock_answer:
            response = client.post(
                "/api/v1/ask-legal-question",
                json={
                    "document_id": "a" * 24,
                    "contract_text": _SAMPLE_CONTRACT,
                    "question": "What are the key risks?",
                },
            )

        assert response.status_code == 200
        mock_answer.assert_called_once_with(
            _SAMPLE_CONTRACT,
            "What are the key risks?",
        )

    def test_expired_document_without_text_returns_gone(self) -> None:
        """An expired ID without fallback text should return HTTP 410."""
        response = client.post(
            "/api/v1/ask-legal-question",
            json={
                "document_id": "a" * 24,
                "question": "What are the key risks?",
            },
        )

        assert response.status_code == 410


class TestCorsPolicy:
    """Verify only configured frontend origins receive CORS permission."""

    def test_allows_local_frontend_origin(self) -> None:
        """The local development frontend should be allowed."""
        response = client.options(
            "/api/v1/upload-contract",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == (
            "http://localhost:3000"
        )

    def test_rejects_unknown_frontend_origin(self) -> None:
        """Untrusted origins should not receive an allow-origin header."""
        response = client.options(
            "/api/v1/upload-contract",
            headers={
                "Origin": "https://malicious.example",
                "Access-Control-Request-Method": "POST",
            },
        )

        assert "access-control-allow-origin" not in response.headers
