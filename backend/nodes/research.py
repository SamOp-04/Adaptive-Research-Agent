from __future__ import annotations

from backend.graph.state import ResearchState, SourceFinding
from backend.skills.source_evaluation import dedupe_findings_by_url, passes_credibility, score_source
from backend.skills.text_cleanup import sanitize_finding_text
from backend.skills.web_research import SearchResult, search_web


async def research_node(state: ResearchState) -> ResearchState:
    questions = state.get("sub_questions") or [state.get("query", "")]
    depth = state.get("depth", "standard")
    per_question = 3 if depth == "quick" else 5 if depth == "standard" else 8
    findings: list[SourceFinding] = []

    for question in questions:
        results = await search_web(question, max_results=per_question)
        for result in results:
            finding = _finding_from_result(question, result)
            if passes_credibility(finding["credibility"]):
                findings.append(finding)

    findings = dedupe_findings_by_url(findings)
    findings.sort(key=lambda item: item.get("credibility", {}).get("score", 0), reverse=True)
    return {"findings": findings}


def _finding_from_result(question: str, result: SearchResult) -> SourceFinding:
    credibility = score_source(
        result.url,
        published_at=result.published_at,
        citations=result.citations,
    )
    return {
        "query": question,
        "title": sanitize_finding_text(result.title),
        "url": result.url,
        "snippet": sanitize_finding_text(result.snippet),
        "published_at": result.published_at,
        "credibility": credibility,
    }
