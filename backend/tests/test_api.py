"""Tests for ClauseGuard AI API endpoints and PII scrubbing logic.

Uses FastAPI's TestClient for synchronous endpoint testing and
directly tests the PII scrubber as a unit.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.legal_schemas import (
    LEGAL_DISCLAIMER,
    ClauseItem,
    RiskLevel,
    RiskResponse,
)
from app.services.pii_scrubber import scrub_pii

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
        assert result.redaction_count >= 1

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
