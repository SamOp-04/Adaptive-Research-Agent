from __future__ import annotations

from backend.graph.state import ResearchState, SourceFinding
from backend.llm.ollama_client import answer_without_sources, synthesize_with_ollama


async def synthesis_node(state: ResearchState) -> ResearchState:
    findings = state.get("findings", [])
    if not findings:
        fallback_answer = await answer_without_sources(state.get("query", ""))
        return {
            "answer": fallback_answer or _no_results_message(),
            "key_findings": [],
        }

    answer = await synthesize_with_ollama(
        state.get("query", ""),
        findings,
        output_type=state.get("output_type", "text"),
    )
    return {
        "answer": answer or _fallback_summary(state.get("query", ""), findings),
        "key_findings": _fallback_key_findings(findings),
    }


def _no_results_message() -> str:
    return (
        "I could not retrieve web results for this query yet. "
        "Check search credentials or network access, then try again."
    )


def _fallback_summary(query: str, findings: list[SourceFinding]) -> str:
    top_findings = sorted(
        findings,
        key=lambda item: item.get("credibility", {}).get("score", 0),
        reverse=True,
    )[:5]
    lines = [f"Research summary for: {query}", ""]
    for index, item in enumerate(top_findings, start=1):
        title = item.get("title") or "Untitled source"
        snippet = item.get("snippet") or "No snippet available."
        url = item.get("url") or ""
        lines.append(f"{index}. {title}: {snippet} ({url})")
    return "\n".join(lines)


def _fallback_key_findings(findings: list[SourceFinding]) -> list[str]:
    key_findings: list[str] = []
    for item in findings[:6]:
        title = item.get("title") or "Source"
        snippet = (item.get("snippet") or "").strip()
        if snippet:
            key_findings.append(f"{title}: {snippet}")
    return key_findings
