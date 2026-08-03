from __future__ import annotations

import json
import re
from typing import Any

from backend.graph.state import Depth, OutputType, ResearchState
from backend.llm.ollama_client import OllamaClient


QueryType = str
VALID_QUERY_TYPES = {"factual", "analytical", "comparative", "exploratory"}
VALID_DEPTHS = {"quick", "standard", "deep"}
VALID_OUTPUT_TYPES = {"text", "chart", "table", "docx", "pdf"}

INTENT_CLASSIFIER_SYSTEM = (
    "You classify research requests for an adaptive research agent. "
    "Return only valid JSON and no prose."
)

INTENT_CLASSIFIER_PROMPT = """Classify this research request.

Recent conversation context, if it helps resolve a follow-up:
{conversation_context}

User request:
{query}

Return exactly this JSON object:
{{
  "query_type": "factual" | "analytical" | "comparative" | "exploratory",
  "depth": "quick" | "standard" | "deep",
  "output_type": "text" | "chart" | "table" | "docx" | "pdf"
}}

Choose the output_type the user would most likely want even when they do not explicitly name a format.
Use "table" for comparisons, rankings, feature matrices, structured pros/cons, or multi-item evaluations.
Use "chart" for numeric trends, time series, distributions, or metric comparisons.
Use "docx" or "pdf" for report-like deliverables, briefs meant to be shared, or long-form formatted output.
Use "text" for direct answers and short explanations.
"""


def _infer_depth(query: str) -> Depth:
    lowered = query.lower()
    if any(token in lowered for token in ("deep", "comprehensive", "literature review", "market map")):
        return "deep"
    if any(token in lowered for token in ("quick", "brief", "summary", "tl;dr")):
        return "quick"
    return "standard"


def _infer_output_type(query: str, current: OutputType | None) -> OutputType:
    if current and current != "text":
        return current

    lowered = query.lower()
    if any(token in lowered for token in ("chart", "graph", "plot", "trend")):
        return "chart"
    if any(token in lowered for token in ("table", "compare", "matrix", "spreadsheet")):
        return "table"
    if "pdf" in lowered:
        return "pdf"
    if any(token in lowered for token in ("docx", "document", "report file")):
        return "docx"
    return "text"


def _infer_query_type(query: str) -> QueryType:
    lowered = query.lower()
    if any(token in lowered for token in ("compare", "versus", " vs ", "matrix", "ranking")):
        return "comparative"
    if any(token in lowered for token in ("why", "impact", "trend", "tradeoff", "analysis")):
        return "analytical"
    if any(token in lowered for token in ("explore", "map", "landscape", "opportunities")):
        return "exploratory"
    return "factual"


async def classify_intent(state: ResearchState) -> ResearchState:
    query = state.get("query", "")
    current_output_type = state.get("output_type")
    llm_classification = await _classify_with_llm(query, state.get("conversation_context", ""))
    if llm_classification:
        output_type = _resolve_output_type(
            llm_classification["output_type"],
            current_output_type,
        )
        return {
            "query_type": llm_classification["query_type"],
            "depth": llm_classification["depth"],
            "output_type": output_type,
        }

    return {
        "query_type": _infer_query_type(query),
        "depth": _infer_depth(query),
        "output_type": _infer_output_type(query, current_output_type),
    }


async def _classify_with_llm(query: str, conversation_context: str = "") -> dict[str, str] | None:
    if not query.strip():
        return None

    messages = [
        {"role": "system", "content": INTENT_CLASSIFIER_SYSTEM},
        {
            "role": "user",
            "content": INTENT_CLASSIFIER_PROMPT.format(
                query=query,
                conversation_context=conversation_context or "None",
            ),
        },
    ]
    try:
        raw = await OllamaClient().chat(messages)
        parsed = _extract_json_object(raw)
    except Exception:
        return None

    return _validate_classification(parsed)


def _extract_json_object(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            raise
        parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict):
        raise ValueError("Intent classifier returned non-object JSON")
    return parsed


def _validate_classification(parsed: dict[str, Any]) -> dict[str, str] | None:
    query_type = str(parsed.get("query_type", "")).strip().lower()
    depth = str(parsed.get("depth", "")).strip().lower()
    output_type = _validate_output_type(parsed)

    if query_type not in VALID_QUERY_TYPES:
        return None
    if depth not in VALID_DEPTHS:
        return None
    if output_type is None:
        return None

    return {
        "query_type": query_type,
        "depth": depth,
        "output_type": output_type,
    }


def _validate_output_type(parsed: dict[str, Any]) -> OutputType | None:
    output_type = str(parsed.get("output_type", "")).strip().lower()
    if output_type not in VALID_OUTPUT_TYPES:
        return None
    return output_type  # type: ignore[return-value]


def _resolve_output_type(inferred: str, current: OutputType | None) -> OutputType:
    if current and current != "text":
        return current
    return inferred  # type: ignore[return-value]
