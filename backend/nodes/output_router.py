from __future__ import annotations

import re
from typing import Any, cast

from backend.graph.state import OutputType, ResearchState
from backend.llm.ollama_client import OllamaClient
from backend.nodes.intent_classifier import _extract_json_object, _validate_output_type
from backend.skills.chart_extraction import (
    ChartPoint,
    chart_points_have_consistent_units,
    coerce_chart_value,
    extract_chart_points_fast,
    normalize_chart_unit,
)
from backend.skills.text_cleanup import sanitize_finding_text


OUTPUT_ROUTER_SYSTEM = (
    "You are the final output router for an adaptive research agent. "
    "Return only valid JSON and no prose."
)

OUTPUT_ROUTER_PROMPT = """The early output_type guess was "text". Decide whether the final answer should stay text or become a structured artifact.

Only choose a different output_type when the evidence clearly supports it.

User request:
{query}

Signals:
- source_count: {source_count}
- numeric_finding_count: {numeric_finding_count}
- comparative_finding_count: {comparative_finding_count}
- answer_has_numeric_signal: {answer_has_numeric}
- answer_has_comparative_signal: {answer_has_comparative}

Findings:
{findings}

Answer:
{answer}

Return exactly this JSON object:
{{
  "output_type": "text" | "chart" | "table" | "docx" | "pdf"
}}

Use "chart" only for numeric trends, time series, distributions, or metric comparisons with extractable values.
Use "table" only for comparisons, rankings, feature matrices, structured pros/cons, or multi-item evaluations.
Prefer "chart" when the request asks how a metric changed, grew, trended, or moved over time and findings contain multiple numeric values.
Prefer "table" when the request asks how named options differ, which option is best, or what tradeoffs exist and findings contain comparison criteria.
Do not choose "docx" or "pdf" unless the user explicitly requested a document format; this late check does not include an explicit document request.
Use "text" when the answer is better as prose or the evidence is ambiguous.
"""

CHART_EXTRACTOR_SYSTEM = (
    "You extract chart-ready numeric data from research findings. "
    "Return only valid JSON and no prose."
)

CHART_EXTRACTOR_PROMPT = """Extract up to 8 chart points from this answer and its findings.

Return exactly this JSON object:
{{
  "points": [
    {{"label": "2001", "value": 50671017, "unit": "people"}}
  ]
}}

Rules:
- label must be what is measured: a year, category, or short metric name.
- label must not be a source title, publication name, URL, or long sentence.
- value must be a plain number, not a string and not a formatted phrase.
- all points must share one consistent axis/unit.
- use units such as "people", "percent", "currency", "ratio", "bps", or "number".
- if the findings do not contain at least 3 points on one clean axis, return {{"points": []}}.

User request:
{query}

Answer:
{answer}

Findings:
{findings}
"""

NUMERIC_RE = re.compile(
    r"(?<![\w.])(?:\$?\d[\d,]*(?:\.\d+)?%?|\d+(?:\.\d+)?\s*(?:x|bps|million|billion|trillion))",
    flags=re.IGNORECASE,
)
COMPARATIVE_RE = re.compile(
    r"\b("
    r"compare|comparison|comparative|differ|differs|different|difference|differences|versus|vs\.?|"
    r"ranking|ranked|rank|best|worst|"
    r"higher|lower|more than|less than|increase|decrease|growth|decline|"
    r"pros|cons|advantages|disadvantages|tradeoffs?|benchmark|metric|score"
    r")\b",
    flags=re.IGNORECASE,
)


async def output_router_node(state: ResearchState) -> ResearchState:
    """Build the artifact for the selected output type, with a late text-only refinement."""
    output_type: OutputType = state.get("output_type", "text")
    findings = cast(list[dict[str, Any]], state.get("findings", []))

    output_type = await _resolve_final_output_type(state, output_type)

    return {"output_type": output_type, "artifact": await _build_artifact(state, output_type, findings)}


async def _resolve_final_output_type(state: ResearchState, output_type: OutputType) -> OutputType:
    if output_type != "text":
        return output_type

    findings = cast(list[dict[str, Any]], state.get("findings", []))
    answer = state.get("answer", "")
    signals = _structure_signals(findings, answer)
    if not _should_refine_text_output(signals):
        return "text"

    refined = await _classify_output_with_llm(state.get("query", ""), findings, answer, signals)
    if refined in {"chart", "table"} and _has_clear_override_signal(refined, signals):
        return refined

    return "text"


async def _classify_output_with_llm(
    query: str,
    findings: list[dict[str, Any]],
    answer: str,
    signals: dict[str, Any],
) -> OutputType | None:
    messages = [
        {"role": "system", "content": OUTPUT_ROUTER_SYSTEM},
        {
            "role": "user",
            "content": OUTPUT_ROUTER_PROMPT.format(
                query=query,
                source_count=signals["source_count"],
                numeric_finding_count=signals["numeric_finding_count"],
                comparative_finding_count=signals["comparative_finding_count"],
                answer_has_numeric=signals["answer_has_numeric"],
                answer_has_comparative=signals["answer_has_comparative"],
                findings=_format_findings_for_prompt(findings),
                answer=answer[:2400],
            ),
        },
    ]
    try:
        raw = await OllamaClient().chat(messages, temperature=0.0)
        parsed = _extract_json_object(raw)
    except Exception:
        return None

    return _validate_output_type(parsed)


async def _extract_chart_points_with_llm(
    query: str,
    answer: str,
    findings: list[dict[str, Any]],
) -> list[ChartPoint] | None:
    messages = [
        {"role": "system", "content": CHART_EXTRACTOR_SYSTEM},
        {
            "role": "user",
            "content": CHART_EXTRACTOR_PROMPT.format(
                query=query,
                answer=answer[:2400],
                findings=_format_findings_for_prompt(findings),
            ),
        },
    ]
    try:
        raw = await OllamaClient().chat(messages, temperature=0.0)
        parsed = _extract_json_object(raw)
    except Exception:
        return None

    return _validate_chart_points(parsed, findings)


def _validate_chart_points(parsed: dict[str, Any], findings: list[dict[str, Any]]) -> list[ChartPoint] | None:
    raw_points = parsed.get("points")
    if not isinstance(raw_points, list):
        return None

    points: list[ChartPoint] = []
    source_titles = [
        str(item.get("title", "")).strip().lower()
        for item in findings
        if str(item.get("title", "")).strip()
    ]
    for raw_point in raw_points[:8]:
        if not isinstance(raw_point, dict):
            return None

        label = str(raw_point.get("label", "")).strip()
        value = coerce_chart_value(raw_point.get("value"))
        unit = normalize_chart_unit(str(raw_point.get("unit", "number")))
        if not label or value is None or unit is None:
            return None
        if _invalid_chart_label(label, source_titles):
            return None

        points.append({"label": label[:32], "value": value, "unit": unit})

    if len(points) < 3:
        return None
    if not chart_points_have_consistent_units(points):
        return None
    return points


def _invalid_chart_label(label: str, source_titles: list[str]) -> bool:
    normalized = label.lower()
    if len(label) > 48:
        return True
    if re.search(r"https?://|www\.|\.com|\.org|\.net", label, flags=re.IGNORECASE):
        return True
    return any(normalized == title[: len(normalized)] and len(normalized) > 12 for title in source_titles)


def _structure_signals(findings: list[dict[str, Any]], answer: str) -> dict[str, Any]:
    finding_texts = [_finding_text(item) for item in findings]
    numeric_finding_count = sum(1 for text in finding_texts if NUMERIC_RE.search(text))
    comparative_finding_count = sum(1 for text in finding_texts if COMPARATIVE_RE.search(text))

    return {
        "source_count": len(findings),
        "numeric_finding_count": numeric_finding_count,
        "comparative_finding_count": comparative_finding_count,
        "answer_has_numeric": bool(NUMERIC_RE.search(answer)),
        "answer_has_comparative": bool(COMPARATIVE_RE.search(answer)),
    }


def _should_refine_text_output(signals: dict[str, Any]) -> bool:
    if signals["source_count"] < 5:
        return False

    numeric_signal = signals["numeric_finding_count"] >= 3 or (
        signals["numeric_finding_count"] >= 2 and signals["answer_has_numeric"]
    )
    comparative_signal = signals["comparative_finding_count"] >= 3 or (
        signals["comparative_finding_count"] >= 2 and signals["answer_has_comparative"]
    )
    return numeric_signal or comparative_signal


def _has_clear_override_signal(output_type: OutputType, signals: dict[str, Any]) -> bool:
    if output_type == "chart":
        return signals["numeric_finding_count"] >= 3 or (
            signals["numeric_finding_count"] >= 2 and signals["answer_has_numeric"]
        )
    if output_type == "table":
        return signals["comparative_finding_count"] >= 3 or (
            signals["comparative_finding_count"] >= 2 and signals["answer_has_comparative"]
        )
    return False


def _format_findings_for_prompt(findings: list[dict[str, Any]]) -> str:
    lines = []
    for index, item in enumerate(findings[:8], start=1):
        lines.append(f"{index}. {_finding_text(item)[:500]}")
    return "\n".join(lines)


def _finding_text(item: dict[str, Any]) -> str:
    return sanitize_finding_text(
        " ".join(
            sanitize_finding_text(item.get(field, ""))
            for field in ("title", "snippet")
            if item.get(field)
        )
    )


async def _build_artifact(
    state: ResearchState,
    output_type: OutputType,
    findings: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if output_type == "chart":
        return await _build_chart_artifact(state, findings)
    if output_type == "table":
        return {
            "type": "table",
            "columns": ["title", "url", "credibility"],
            "rows": [
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "credibility": round(item.get("credibility", {}).get("score", 0), 2),
                }
                for item in findings[:12]
            ],
        }
    if output_type in ("docx", "pdf"):
        from backend.skills.document_generation import generate_document

        path = generate_document(
            state.get("answer", ""),
            output_type=output_type,
            title=state.get("query", "Adaptive Research Report"),
            key_findings=state.get("key_findings", []),
            sources=findings,
        )
        return {
            "type": output_type,
            "href": f"/files/{path.name}",
            "fileName": path.name,
        }

    return None


async def _build_chart_artifact(state: ResearchState, findings: list[dict[str, Any]]) -> dict[str, Any] | None:
    chart_findings = findings[:8]
    regex_points = extract_chart_points_fast(
        state.get("query", ""),
        state.get("answer", ""),
        chart_findings,
    )
    points = regex_points or []

    if len(points) < 3:
        llm_points = await _extract_chart_points_with_llm(
            state.get("query", ""),
            state.get("answer", ""),
            chart_findings,
        )
        if llm_points:
            points = llm_points

    if len(points) < 3:
        return None

    return {
        "type": "chart",
        "data": [
            _chart_datum_from_point(point, chart_findings, index)
            for index, point in enumerate(points[:8])
        ],
    }


def _chart_datum_from_point(
    point: ChartPoint,
    findings: list[dict[str, Any]],
    fallback_index: int,
) -> dict[str, Any]:
    source_index = point.get("source_index", fallback_index)
    if not isinstance(source_index, int) or source_index < 0 or source_index >= len(findings):
        source_index = min(fallback_index, max(len(findings) - 1, 0))
    item = findings[source_index] if findings else {}
    label = str(point.get("label", f"Point {fallback_index + 1}")).strip()[:32]
    return {
        "label": label,
        "name": label,
        "value": _chart_value(point.get("value", 0)),
        "credibility": round(item.get("credibility", {}).get("score", 0), 2),
        "title": sanitize_finding_text(item.get("title", "")),
        "findingText": _finding_text(item),
    }


def _chart_value(value: object) -> float | int:
    numeric = coerce_chart_value(value)
    if numeric is None:
        return 0
    if numeric.is_integer():
        return int(numeric)
    return round(numeric, 4)
