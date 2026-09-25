"""PII Scrubbing Service — redacts personally identifiable information.

Applies regex-based redaction for emails, phone numbers, and SSN-format
strings *before* any text is transmitted to external AI services.
"""

import re
from typing import NamedTuple


class ScrubResult(NamedTuple):
    """Immutable result of a PII scrubbing operation."""

    cleaned_text: str
    redaction_count: int


# ---------------------------------------------------------------------------
# Pre-compiled patterns (compiled once at module load for performance)
# ---------------------------------------------------------------------------

_EMAIL_PATTERN: re.Pattern[str] = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)

_PHONE_PATTERN: re.Pattern[str] = re.compile(
    r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
)

_SSN_PATTERN: re.Pattern[str] = re.compile(
    r"\b\d{3}-\d{2}-\d{4}\b"
)

# Ordered list so broader patterns don't shadow narrower ones.
_SCRUB_RULES: list[tuple[re.Pattern[str], str]] = [
    (_SSN_PATTERN, "[SSN_REDACTED]"),
    (_EMAIL_PATTERN, "[EMAIL_REDACTED]"),
    (_PHONE_PATTERN, "[PHONE_REDACTED]"),
]


def scrub_pii(text: str) -> ScrubResult:
    """Remove PII from *text* before sending to external AI services.

    Currently redacts:
    - Email addresses  → ``[EMAIL_REDACTED]``
    - US phone numbers → ``[PHONE_REDACTED]``
    - SSN-format nums  → ``[SSN_REDACTED]``

    Args:
        text: Raw contract text that may contain PII.

    Returns:
        A ``ScrubResult`` with the sanitised text and the total number of
        redactions applied.
    """
    total_redactions: int = 0

    for pattern, replacement in _SCRUB_RULES:
        matches: list[str] = pattern.findall(text)
        total_redactions += len(matches)
        text = pattern.sub(replacement, text)

    return ScrubResult(cleaned_text=text, redaction_count=total_redactions)
