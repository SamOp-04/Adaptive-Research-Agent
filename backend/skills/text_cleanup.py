from __future__ import annotations

import re


REPEATED_NON_TEXT_RE = re.compile(r"(?:[^\w\s]){3,}", flags=re.UNICODE)
WHITESPACE_RE = re.compile(r"\s+")


def sanitize_finding_text(value: object) -> str:
    text = str(value or "")
    text = REPEATED_NON_TEXT_RE.sub(" ", text)
    return WHITESPACE_RE.sub(" ", text).strip()
