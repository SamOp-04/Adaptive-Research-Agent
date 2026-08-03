from __future__ import annotations

from html import unescape
import re


REPEATED_NON_TEXT_RE = re.compile(r"(?:[^\w\s]){3,}", flags=re.UNICODE)
WHITESPACE_RE = re.compile(r"\s+")
HTML_TAG_RE = re.compile(r"<[^>]+>")
SVG_PATH_DATA_RE = re.compile(
    r"\b(?:[mMlLhHvVcCsSqQtTaAzZ][-+]?\d[\d\s,.\-eE]*){2,}",
)
SVG_ATTRIBUTE_RE = re.compile(
    r"\b(?:fill|stroke|clip-path|d|viewBox|xmlns|path|svg)=(?:\"[^\"]*\"|'[^']*'|[^\s>]+)",
    flags=re.IGNORECASE,
)
URL_ENCODED_FRAGMENT_RE = re.compile(r"url\(%23[^)]+\)", flags=re.IGNORECASE)
HEX_COLOR_RE = re.compile(r"#[0-9a-f]{3,8}\b", flags=re.IGNORECASE)
IMAGE_PLACEHOLDER_RE = re.compile(
    r"\b(?:Report Ad)?\s*Image\s+\d+(?::\s*dot image pixel)?",
    flags=re.IGNORECASE,
)
COOKIE_CHROME_RE = re.compile(
    r"\b(?:Cookies?,?\s+opens new tab|Manage Cookies|Accept Cookies|Reject Cookies|"
    r"Advertisement\s*[.\u00b7-]\s*Scroll to continue|Scroll to continue|Report Ad)\b",
    flags=re.IGNORECASE,
)
SCRIPT_STYLE_BLOCK_RE = re.compile(
    r"<(?:script|style|svg)\b[^>]*>.*?</(?:script|style|svg)>",
    flags=re.IGNORECASE | re.DOTALL,
)
MARKUP_NOISE_RE = re.compile(
    r"\b(?:paint\d+linear|linearGradient|clipPath|currentColor|pathdata)\b",
    flags=re.IGNORECASE,
)


def sanitize_finding_text(value: object) -> str:
    text = unescape(str(value or ""))
    text = SCRIPT_STYLE_BLOCK_RE.sub(" ", text)
    text = SVG_ATTRIBUTE_RE.sub(" ", text)
    text = URL_ENCODED_FRAGMENT_RE.sub(" ", text)
    text = SVG_PATH_DATA_RE.sub(" ", text)
    text = IMAGE_PLACEHOLDER_RE.sub(" ", text)
    text = COOKIE_CHROME_RE.sub(" ", text)
    text = HTML_TAG_RE.sub(" ", text)
    text = HEX_COLOR_RE.sub(" ", text)
    text = MARKUP_NOISE_RE.sub(" ", text)
    text = REPEATED_NON_TEXT_RE.sub(" ", text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    return _drop_noisy_sentences(text)


def _drop_noisy_sentences(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    kept: list[str] = []
    for sentence in sentences:
        stripped = sentence.strip()
        if not stripped:
            continue
        if _looks_like_markup_noise(stripped):
            continue
        kept.append(stripped)
    return " ".join(kept)


def _looks_like_markup_noise(text: str) -> bool:
    if len(text) < 24:
        return False

    alpha_count = len(re.findall(r"[A-Za-z]", text))
    digit_count = len(re.findall(r"\d", text))
    punctuation_count = len(re.findall(r"[#%<>{}=()/;:'\".,-]", text))
    token_count = len(text.split())

    if punctuation_count > alpha_count and digit_count > 8:
        return True
    if token_count <= 3 and digit_count > alpha_count:
        return True
    return False
