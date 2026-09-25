"""Bounded in-memory cache for scrubbed contract context."""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class _CacheEntry:
    cleaned_text: str
    expires_at: float


_CACHE_TTL_SECONDS = int(os.getenv("CONTEXT_CACHE_TTL_SECONDS", "900"))
_CACHE_MAX_ENTRIES = int(os.getenv("CONTEXT_CACHE_MAX_ENTRIES", "100"))
_entries: dict[str, _CacheEntry] = {}


def _document_id(cleaned_text: str) -> str:
    return hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()[:24]


def store(cleaned_text: str) -> str:
    """Store scrubbed text and return a non-sensitive document identifier."""
    now = time.monotonic()
    expired = [key for key, entry in _entries.items() if entry.expires_at <= now]
    for key in expired:
        _entries.pop(key, None)

    document_id = _document_id(cleaned_text)
    _entries[document_id] = _CacheEntry(
        cleaned_text=cleaned_text,
        expires_at=now + _CACHE_TTL_SECONDS,
    )

    while len(_entries) > _CACHE_MAX_ENTRIES:
        oldest_key = min(_entries, key=lambda key: _entries[key].expires_at)
        _entries.pop(oldest_key, None)

    return document_id


def get(document_id: str) -> str | None:
    """Return cached scrubbed text when the ID is valid and unexpired."""
    entry = _entries.get(document_id)
    if entry is None:
        return None
    if entry.expires_at <= time.monotonic():
        _entries.pop(document_id, None)
        return None
    return entry.cleaned_text


def clear() -> None:
    """Clear cached contexts, primarily for tests and graceful shutdowns."""
    _entries.clear()