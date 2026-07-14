from __future__ import annotations

import pytest

from backend.nodes.research import research_node
from backend.skills import web_research
from backend.skills.web_research import SearchResult


@pytest.mark.asyncio
async def test_research_node_scores_results(monkeypatch):
    async def fake_search_web(query: str, *, max_results: int):
        return [
            SearchResult(
                title="Test Source",
                url="https://nih.gov/example",
                snippet="Useful evidence.",
                published_at="2026-01-01T00:00:00+00:00",
            )
        ]

    monkeypatch.setattr("backend.nodes.research.search_web", fake_search_web)

    state = await research_node({"query": "test query", "sub_questions": ["test query"], "depth": "quick"})

    assert state["findings"][0]["title"] == "Test Source"
    assert state["findings"][0]["credibility"]["tier"] == "high"


@pytest.mark.asyncio
async def test_research_node_dedupes_repeated_urls_across_sub_questions(monkeypatch):
    async def fake_search_web(query: str, *, max_results: int):
        if query == "first question":
            return [
                SearchResult(
                    title="Lower duplicate",
                    url="https://Example.com/report/?utm_source=planner",
                    snippet="Lower scoring duplicate.",
                )
            ]
        return [
            SearchResult(
                title="Higher duplicate",
                url="http://www.example.com/report/",
                snippet="Higher scoring duplicate.",
            )
        ]

    def fake_score_source(url: str, **kwargs):
        score = 0.9 if url.startswith("http://www.") else 0.6
        return {"domain": "example.com", "tier": "unknown", "score": score}

    monkeypatch.setattr("backend.nodes.research.search_web", fake_search_web)
    monkeypatch.setattr("backend.nodes.research.score_source", fake_score_source)

    state = await research_node(
        {
            "query": "dedupe sources",
            "sub_questions": ["first question", "second question"],
            "depth": "quick",
        }
    )

    assert len(state["findings"]) == 1
    assert state["findings"][0]["title"] == "Higher duplicate"
    assert state["findings"][0]["credibility"]["score"] == 0.9


@pytest.mark.asyncio
async def test_search_web_falls_back_after_tavily_failure(monkeypatch):
    class FakeSettings:
        tavily_api_key = "configured"

    def fake_tavily_search(query: str, max_results: int):
        raise TimeoutError("tavily timed out")

    def fake_duckduckgo_search(query: str, max_results: int):
        return [
            SearchResult(
                title="Fallback Source",
                url="https://example.com/fallback",
                snippet="Fallback result.",
            )
        ]

    monkeypatch.setattr(web_research, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(web_research, "_tavily_search", fake_tavily_search)
    monkeypatch.setattr(web_research, "_duckduckgo_search", fake_duckduckgo_search)

    results = await web_research.search_web("test query", max_results=3)

    assert results[0].title == "Fallback Source"


@pytest.mark.asyncio
async def test_search_web_returns_empty_after_provider_failures(monkeypatch):
    class FakeSettings:
        tavily_api_key = None

    def fake_duckduckgo_search(query: str, max_results: int):
        raise TimeoutError("duckduckgo timed out")

    monkeypatch.setattr(web_research, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(web_research, "_duckduckgo_search", fake_duckduckgo_search)

    assert await web_research.search_web("test query", max_results=3) == []
