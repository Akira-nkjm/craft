"""Shared redaction helpers for session persistence hooks."""
from __future__ import annotations

import re


REDACTIONS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"/Users/[^/\s]+"), "/Users/<redacted>"),
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE), "<redacted-email>"),
    (re.compile(r"\b(?:sk|xoxb|xoxp|ghp|github_pat)_[A-Za-z0-9_\-]{12,}\b"), "<redacted-token>"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{12,}\b"), "<redacted-token>"),
    (re.compile(r"\bAKIA[0-9A-Z]{12,}\b"), "<redacted-token>"),
    (
        re.compile(
            r"(?i)\b(password|passwd|pwd|token|api[_-]?key|secret)\b\s*[:=]\s*['\"]?[^'\"\s,;]+"
        ),
        r"\1=<redacted>",
    ),
]


def redact_text(value: str) -> str:
    """Redact common local paths, email addresses, and token-like secrets."""
    redacted = value
    for pattern, replacement in REDACTIONS:
        redacted = pattern.sub(replacement, redacted)
    return redacted
