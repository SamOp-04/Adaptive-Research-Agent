from __future__ import annotations

from typing import Any, Literal, TypedDict
from uuid import uuid4


Depth = Literal["quick", "standard", "deep"]
OutputType = Literal["text", "chart", "table", "docx", "pdf"]
StepStatus = Literal["running", "completed", "failed"]


class StepEvent(TypedDict, total=False):
    step: str
    status: StepStatus
    message: str
    payload: dict[str, Any]
    timestamp: str


class SourceFinding(TypedDict, total=False):
    query: str
    title: str
    url: str
    snippet: str
    published_at: str | None
    credibility: dict[str, Any]


class ResearchState(TypedDict, total=False):
    session_id: str
    query: str
    query_type: Literal["factual", "analytical", "comparative", "exploratory"]
    depth: Depth
    output_type: OutputType
    sub_questions: list[str]
    findings: list[SourceFinding]
    key_findings: list[str]
    answer: str
    artifact: dict[str, Any] | None
    events: list[StepEvent]
    errors: list[str]


def initial_state(
    query: str,
    *,
    session_id: str | None = None,
    output_type: OutputType | None = None,
) -> ResearchState:
    return {
        "session_id": session_id or str(uuid4()),
        "query": query,
        "depth": "standard",
        "output_type": output_type or "text",
        "sub_questions": [],
        "findings": [],
        "key_findings": [],
        "answer": "",
        "artifact": None,
        "events": [],
        "errors": [],
    }
