from __future__ import annotations

import math
import re
from typing import Any, Literal, TypedDict


UnitGroup = Literal["count", "currency", "percent", "ratio", "number", "bps"]


class ChartPoint(TypedDict, total=False):
    label: str
    value: float
    unit: str
    source_index: int


class _Candidate(TypedDict):
    label: str
    value: float
    unit: UnitGroup
    source_index: int
    score: float


NUMBER_RE = re.compile(
    r"(?<![\w.])(?P<number>\$?\d[\d,]*(?:\.\d+)?%?(?:\s*(?:crore|lakh|million|billion|trillion|thousand|bps|bn|mn|m|b|k|x)\b)?)",
    flags=re.IGNORECASE,
)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
CATEGORY_RE = re.compile(
    r"\b(male|males|female|females|men|women|boys|girls|urban|rural)\b",
    flags=re.IGNORECASE,
)
PROPER_NOUN_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

# Sentence-leading / mid-sentence capitalized words that are not real entity names.
# These get capitalized in normal prose ("More than 90%...", "According to...") and
# would otherwise be picked up by PROPER_NOUN_RE as a fake chart label.
NON_ENTITY_WORDS = {
    "more", "less", "most", "least", "over", "under", "about", "roughly", "nearly",
    "almost", "approximately", "around", "than", "the", "this", "that", "these",
    "those", "these", "total", "overall", "according", "source", "sources", "also",
    "however", "meanwhile", "currently", "today", "now", "in", "by", "as", "of",
    "for", "with", "since", "up", "down", "each", "every", "some", "many", "few",
    "it", "its", "we", "they", "there", "here", "one", "two", "three", "four",
    "five", "figure", "chart", "table", "data", "report", "reports", "study",
    "studies", "note", "notes", "key", "top",
}

UNIT_PATTERN = re.compile(
    r"\b(crore|lakh|million|billion|trillion|thousand|bps|bn|mn|m|b|k|x)\b",
    flags=re.IGNORECASE,
)

COUNT_HINT_RE = re.compile(
    r"\b(population|people|persons|residents|users|customers|subscribers|employees|males|females|men|women)\b",
    flags=re.IGNORECASE,
)
PERCENT_HINT_RE = re.compile(r"\b(percent|percentage|share|rate|growth|margin|cagr)\b", flags=re.IGNORECASE)
RATIO_HINT_RE = re.compile(r"\b(ratio|per\s+100|per\s+1,?000|x)\b", flags=re.IGNORECASE)
CURRENCY_HINT_RE = re.compile(r"\b(revenue|sales|market cap|spend|cost|price|budget|profit|income)\b", flags=re.IGNORECASE)


def extract_chart_points_fast(
    query: str,
    answer: str,
    findings: list[dict[str, Any]],
    *,
    max_points: int = 8,
) -> list[ChartPoint] | None:
    """Extract one clean chart point per finding when the numeric axis is obvious.

    This is intentionally conservative. Mixed units return None so the caller can
    try the LLM fallback instead of turning unrelated facts into one misleading axis.
    """

    candidates: list[_Candidate] = []
    search_context = f"{query} {answer}"
    for source_index, finding in enumerate(findings[:max_points]):
        candidate = _best_candidate_for_finding(search_context, finding, source_index)
        if candidate:
            candidates.append(candidate)

    if not candidates:
        return None

    units = {candidate["unit"] for candidate in candidates}
    if len(units) != 1:
        return None

    return [
        {
            "label": candidate["label"],
            "value": candidate["value"],
            "unit": candidate["unit"],
            "source_index": candidate["source_index"],
        }
        for candidate in candidates
    ]


def normalize_chart_unit(unit: str) -> UnitGroup | None:
    normalized = unit.strip().lower()
    if normalized in {"count", "people", "person", "persons", "population", "users", "customers"}:
        return "count"
    if normalized in {"currency", "money", "usd", "dollar", "dollars", "$"}:
        return "currency"
    if normalized in {"percent", "percentage", "%"}:
        return "percent"
    if normalized in {"ratio", "multiple", "x"}:
        return "ratio"
    if normalized == "bps":
        return "bps"
    if normalized in {"number", "plain", ""}:
        return "number"
    return None


def chart_points_have_consistent_units(points: list[ChartPoint]) -> bool:
    units = {
        normalize_chart_unit(str(point.get("unit", "")))
        for point in points
        if str(point.get("unit", "")).strip()
    }
    units.discard(None)
    return len(units) <= 1


def coerce_chart_value(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
    elif isinstance(value, str):
        parsed = _parse_number(value, "", "")
        if parsed is None:
            return None
        numeric = parsed[0]
    else:
        return None

    if not math.isfinite(numeric):
        return None
    return numeric


def _best_candidate_for_finding(search_context: str, finding: dict[str, Any], source_index: int) -> _Candidate | None:
    text = " ".join(
        str(finding.get(field, "")).strip()
        for field in ("title", "snippet")
        if finding.get(field)
    )
    if not text.strip():
        return None

    candidates: list[_Candidate] = []
    for sentence in _sentences(text):
        for match in NUMBER_RE.finditer(sentence):
            if _is_year_value(match.group("number")):
                continue
            parsed = _parse_number(match.group("number"), sentence, search_context)
            if parsed is None:
                continue
            value, unit = parsed
            label = _label_for_match(sentence, match)
            if not label:
                continue
            score = _candidate_score(label, unit, sentence, search_context)
            if score <= 0:
                continue
            candidates.append(
                {
                    "label": label,
                    "value": value,
                    "unit": unit,
                    "source_index": source_index,
                    "score": score,
                }
            )

    if not candidates:
        return None
    return max(candidates, key=lambda candidate: candidate["score"])


def _sentences(text: str) -> list[str]:
    sentences = [part.strip() for part in SENTENCE_SPLIT_RE.split(text) if part.strip()]
    return sentences or [text.strip()]


def _parse_number(raw: str, sentence: str, search_context: str) -> tuple[float, UnitGroup] | None:
    stripped = raw.strip()
    unit_match = UNIT_PATTERN.search(stripped)
    unit_token = unit_match.group(1).lower() if unit_match else ""
    is_percent = "%" in stripped or PERCENT_HINT_RE.search(_window_around(sentence, stripped)) is not None
    is_currency = stripped.startswith("$") or CURRENCY_HINT_RE.search(search_context) is not None and "$" in sentence

    numeric_text = re.sub(r"[$,%]", "", stripped)
    numeric_text = UNIT_PATTERN.sub("", numeric_text).strip().replace(",", "")
    try:
        value = float(numeric_text)
    except ValueError:
        return None

    unit: UnitGroup = "number"
    multiplier = 1.0
    if unit_token in {"crore"}:
        multiplier = 10_000_000
        unit = "count"
    elif unit_token in {"lakh"}:
        multiplier = 100_000
        unit = "count"
    elif unit_token in {"million", "mn", "m"}:
        multiplier = 1_000_000
        unit = "currency" if is_currency else "count"
    elif unit_token in {"billion", "bn", "b"}:
        multiplier = 1_000_000_000
        unit = "currency" if is_currency else "count"
    elif unit_token == "trillion":
        multiplier = 1_000_000_000_000
        unit = "currency" if is_currency else "count"
    elif unit_token in {"thousand", "k"}:
        multiplier = 1_000
        unit = "currency" if is_currency else "count"
    elif unit_token == "bps":
        unit = "bps"
    elif unit_token == "x":
        unit = "ratio"
    elif is_percent:
        unit = "percent"
    elif is_currency:
        unit = "currency"
    elif RATIO_HINT_RE.search(_window_around(sentence, stripped)):
        unit = "ratio"
    elif COUNT_HINT_RE.search(sentence) or COUNT_HINT_RE.search(search_context):
        unit = "count"

    return value * multiplier, unit


def _window_around(sentence: str, needle: str, radius: int = 40) -> str:
    index = sentence.lower().find(needle.lower())
    if index < 0:
        return sentence
    start = max(0, index - radius)
    end = min(len(sentence), index + len(needle) + radius)
    return sentence[start:end]


def _is_year_value(raw: str) -> bool:
    cleaned = raw.strip().replace(",", "")
    return bool(YEAR_RE.fullmatch(cleaned))


def _label_for_match(sentence: str, match: re.Match[str]) -> str | None:
    year_label = _nearest_year(sentence, match)
    if year_label:
        return year_label

    category_label = _nearest_category(sentence, match)
    if category_label:
        return category_label

    if "%" in match.group("number"):
        return _metric_label(sentence, match) or "Percent"

    proper_label = _nearest_proper_noun(sentence, match)
    if proper_label:
        return proper_label

    return None


def _nearest_year(sentence: str, match: re.Match[str]) -> str | None:
    nearest: tuple[int, str] | None = None
    for year_match in YEAR_RE.finditer(sentence):
        distance = min(abs(year_match.end() - match.start()), abs(year_match.start() - match.end()))
        if distance <= 120 and not _has_intervening_measurement(sentence, year_match, match) and (
            nearest is None or distance < nearest[0]
        ):
            nearest = (distance, year_match.group(0))
    return nearest[1] if nearest else None


def _has_intervening_measurement(
    sentence: str,
    year_match: re.Match[str],
    value_match: re.Match[str],
) -> bool:
    start = min(year_match.end(), value_match.end())
    end = max(year_match.start(), value_match.start())
    between = sentence[start:end]
    return any(not _is_year_value(match.group("number")) for match in NUMBER_RE.finditer(between))


def _nearest_category(sentence: str, match: re.Match[str]) -> str | None:
    nearest: tuple[int, str] | None = None
    for category_match in CATEGORY_RE.finditer(sentence):
        distance = min(abs(category_match.end() - match.start()), abs(category_match.start() - match.end()))
        if distance <= 50 and (nearest is None or distance < nearest[0]):
            nearest = (distance, category_match.group(1).capitalize())
    return nearest[1] if nearest else None


def _nearest_proper_noun(sentence: str, match: re.Match[str]) -> str | None:
    prefix = sentence[: match.start()]
    nearest: tuple[int, str] | None = None
    for proper_match in PROPER_NOUN_RE.finditer(prefix):
        label = proper_match.group(1).strip()
        if _is_non_entity_label(label):
            continue
        distance = match.start() - proper_match.end()
        if distance <= 50 and (nearest is None or distance < nearest[0]):
            nearest = (distance, label)
    return nearest[1] if nearest else None


def _is_non_entity_label(label: str) -> bool:
    words = label.lower().split()
    if not words:
        return True
    # Reject if every word in the candidate label is a common non-entity word
    # (e.g. "More Than", "According To") rather than an actual proper noun.
    if all(word in NON_ENTITY_WORDS for word in words):
        return True
    # Reject if the label's first word is a common sentence-leading/quantifier
    # word immediately followed by a capitalized non-entity word, which is the
    # classic false-positive shape ("More Than", "Over Half").
    if words[0] in NON_ENTITY_WORDS and len(words) > 1 and words[1] in NON_ENTITY_WORDS:
        return True
    return False


def _metric_label(sentence: str, match: re.Match[str]) -> str | None:
    prefix = sentence[max(0, match.start() - 80) : match.start()]
    metric_match = re.search(
        r"\b(growth rate|rate|share|percentage|percent|margin|cagr)\b",
        prefix,
        flags=re.IGNORECASE,
    )
    if metric_match:
        return metric_match.group(1).title()
    return None


def _candidate_score(label: str, unit: UnitGroup, sentence: str, search_context: str) -> float:
    score = 1.0
    if YEAR_RE.fullmatch(label):
        score += 8
    if CATEGORY_RE.fullmatch(label):
        score += 6
    if unit == "percent":
        score += 5
    if unit == "count" and COUNT_HINT_RE.search(search_context):
        score += 5
    if COUNT_HINT_RE.search(search_context) and unit != "count":
        score -= 8
    if unit == "percent" and PERCENT_HINT_RE.search(search_context):
        score += 4
    if PERCENT_HINT_RE.search(search_context) and unit != "percent":
        score -= 3
    if unit == "ratio" and RATIO_HINT_RE.search(search_context):
        score += 4
    if unit == "ratio" and not RATIO_HINT_RE.search(search_context):
        score -= 6
    if len(label) > 28:
        score -= 4
    if re.search(r"https?://|\.com|\.org|\.net", label, flags=re.IGNORECASE):
        score -= 10
    if not re.search(r"\d|male|female|men|women|urban|rural", label, flags=re.IGNORECASE):
        score -= 1
    if PERCENT_HINT_RE.search(sentence) and unit == "percent":
        score += 2
    return score
