from __future__ import annotations

import re

from backend.graph.state import ResearchState, SourceFinding
from backend.skills.source_evaluation import dedupe_findings_by_url, passes_credibility, score_source
from backend.skills.text_cleanup import sanitize_finding_text
from backend.skills.web_research import SearchResult, search_web


STOPWORDS = {
    "about",
    "across",
    "after",
    "also",
    "and",
    "around",
    "best",
    "between",
    "could",
    "data",
    "does",
    "evidence",
    "findings",
    "from",
    "have",
    "into",
    "latest",
    "more",
    "most",
    "provide",
    "question",
    "recent",
    "reputable",
    "research",
    "should",
    "source",
    "sources",
    "that",
    "their",
    "there",
    "these",
    "this",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
}
GENERIC_TOPIC_TERMS = {
    "analysis",
    "brief",
    "compare",
    "comparison",
    "context",
    "criteria",
    "document",
    "hunger",
    "impact",
    "protest",
    "protests",
    "report",
    "summary",
}
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9'-]*")


async def research_node(state: ResearchState) -> ResearchState:
    questions = state.get("sub_questions") or [state.get("query", "")]
    root_query = state.get("query", "")
    depth = state.get("depth", "standard")
    per_question = 3 if depth == "quick" else 5 if depth == "standard" else 8
    findings: list[SourceFinding] = []

    for question in questions:
        results = await search_web(question, max_results=per_question)
        for result in results:
            finding = _finding_from_result(question, result)
            topical_relevance = topical_relevance_score(root_query, question, finding)
            finding["credibility"]["topical_relevance"] = topical_relevance
            if topical_relevance > 0 and passes_credibility(finding["credibility"]):
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


def topical_relevance_score(root_query: str, search_question: str, finding: SourceFinding) -> float:
    """Score topical fit separately from domain authority.

    High-trust domains are not automatically relevant. A .gov page about bid
    protests should not pass for a named-person hunger protest query just
    because the domain itself is trustworthy.
    """

    root_terms = _meaningful_terms(root_query)
    if not root_terms:
        return 1.0

    candidate_text = " ".join(
        str(finding.get(field, ""))
        for field in ("title", "snippet", "url")
        if finding.get(field)
    )
    candidate_terms = _meaningful_terms(candidate_text)
    if not candidate_terms:
        return 0.0

    named_terms = _named_query_terms(root_query)
    if named_terms and not (named_terms & candidate_terms):
        return 0.0

    matched_root_terms = root_terms & candidate_terms
    if len(matched_root_terms) >= 2:
        return round(min(1.0, len(matched_root_terms) / max(len(root_terms), 1)), 3)

    question_terms = _meaningful_terms(search_question)
    matched_question_terms = question_terms & candidate_terms
    if len(matched_root_terms) == 1 and len(matched_question_terms) >= 2:
        return 0.35

    if len(root_terms) <= 2 and matched_root_terms:
        return 0.5

    return 0.0


def _meaningful_terms(text: str) -> set[str]:
    terms: set[str] = set()
    for raw in TOKEN_RE.findall(text.lower()):
        term = _normalize_term(raw)
        if len(term) < 3 or term in STOPWORDS:
            continue
        terms.add(term)
    return terms


def _named_query_terms(query: str) -> set[str]:
    named: set[str] = set()
    tokens = TOKEN_RE.findall(query)
    for index, token in enumerate(tokens):
        normalized = _normalize_term(token.lower())
        if len(normalized) < 3 or normalized in STOPWORDS or normalized in GENERIC_TOPIC_TERMS:
            continue
        if token.isupper() or (token[:1].isupper() and index > 0):
            named.add(normalized)
    return named


def _normalize_term(term: str) -> str:
    normalized = term.strip("'").replace("'s", "")
    if len(normalized) > 4 and normalized.endswith("ies"):
        return f"{normalized[:-3]}y"
    if len(normalized) > 4 and normalized.endswith("es"):
        return normalized[:-2]
    if len(normalized) > 3 and normalized.endswith("s"):
        return normalized[:-1]
    return normalized
