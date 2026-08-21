from __future__ import annotations

import pytest

from backend.nodes.intent_classifier import classify_intent
from backend.nodes.output_router import _classify_output_with_llm, output_router_node


@pytest.mark.asyncio
async def test_intent_classifier_uses_llm_output_type(monkeypatch):
    async def fake_classify_with_llm(query: str, conversation_context: str = ""):
        return {
            "needs_research": "true",
            "query_type": "comparative",
            "depth": "standard",
            "output_type": "table",
        }

    monkeypatch.setattr("backend.nodes.intent_classifier._classify_with_llm", fake_classify_with_llm)

    state = await classify_intent({"query": "Which vendor is best for our workflow?"})

    assert state["output_type"] == "table"
    assert state["query_type"] == "comparative"


@pytest.mark.asyncio
async def test_intent_classifier_marks_greeting_as_not_research(monkeypatch):
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("casual requests should not call the intent LLM")

    monkeypatch.setattr("backend.nodes.intent_classifier._classify_with_llm", fail_if_called)

    state = await classify_intent({"query": "hello how are you"})

    assert state["needs_research"] is False


@pytest.mark.asyncio
async def test_intent_classifier_falls_back_to_keywords(monkeypatch):
    async def fake_classify_with_llm(query: str, conversation_context: str = ""):
        return None

    monkeypatch.setattr("backend.nodes.intent_classifier._classify_with_llm", fake_classify_with_llm)

    state = await classify_intent({"query": "compare these options in a table"})

    assert state["output_type"] == "table"


@pytest.mark.asyncio
async def test_output_router_builds_chart_artifact(monkeypatch):
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("late router LLM should not run for non-text output types")

    monkeypatch.setattr("backend.nodes.output_router._classify_output_with_llm", fail_if_called)

    state = await output_router_node(
        {
            "query": "show a chart",
            "output_type": "chart",
            "answer": "Gujarat population rose from 5.07 crore in 2001 to 6.04 crore in 2011 and 7.18 crore in 2026.",
            "findings": [
                {
                    "title": "Gujarat population 2001",
                    "url": "https://example.com",
                    "snippet": "In 2001, Gujarat population was 5.07 crore. |||||||||||||| --- --- ===",
                    "credibility": {"score": 0.81},
                },
                {
                    "title": "Gujarat population 2011",
                    "url": "https://example.com/b",
                    "snippet": "In 2011, Gujarat population was 6.04 crore.",
                    "credibility": {"score": 0.72},
                },
                {
                    "title": "Gujarat population 2026",
                    "url": "https://example.com/c",
                    "snippet": "In 2026, Gujarat population is projected at 7.18 crore.",
                    "credibility": {"score": 0.63},
                },
            ],
        }
    )

    assert state["artifact"]["type"] == "chart"
    assert state["artifact"]["data"][0]["label"] == "2001"
    assert state["artifact"]["data"][0]["value"] == 50700000
    assert state["artifact"]["data"][0]["credibility"] == 0.81
    assert "Gujarat population" in state["artifact"]["data"][0]["findingText"]
    assert "|" not in state["artifact"]["data"][0]["findingText"]
    assert "---" not in state["artifact"]["data"][0]["findingText"]


@pytest.mark.asyncio
async def test_output_router_skips_chart_artifact_for_fewer_than_three_points(monkeypatch):
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("late router LLM should not run for non-text output types")

    monkeypatch.setattr("backend.nodes.output_router._classify_output_with_llm", fail_if_called)

    async def fake_extract_chart_points_with_llm(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "backend.nodes.output_router._extract_chart_points_with_llm",
        fake_extract_chart_points_with_llm,
    )

    state = await output_router_node(
        {
            "query": "show a chart",
            "output_type": "chart",
            "findings": [
                {
                    "title": "Source A",
                    "url": "https://example.com",
                    "credibility": {"score": 0.81},
                }
            ],
            "answer": "A one-point chart should stay a text summary.",
        }
    )

    assert state["output_type"] == "chart"
    assert state["artifact"] is None


@pytest.mark.asyncio
async def test_output_router_chart_uses_llm_extraction_when_regex_has_too_few_points(monkeypatch):
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("late router LLM should not run for non-text output types")

    async def fake_extract_chart_points_with_llm(query, answer, findings):
        return [
            {"label": "Q1", "value": 10, "unit": "number"},
            {"label": "Q2", "value": 14, "unit": "number"},
            {"label": "Q3", "value": 18, "unit": "number"},
        ]

    monkeypatch.setattr("backend.nodes.output_router._classify_output_with_llm", fail_if_called)
    monkeypatch.setattr(
        "backend.nodes.output_router._extract_chart_points_with_llm",
        fake_extract_chart_points_with_llm,
    )

    state = await output_router_node(
        {
            "query": "show quarterly adoption as a chart",
            "output_type": "chart",
            "findings": [
                {"title": "Adoption source A", "snippet": "The report discusses adoption.", "credibility": {"score": 0.8}},
                {"title": "Adoption source B", "snippet": "The report compares adoption.", "credibility": {"score": 0.7}},
                {"title": "Adoption source C", "snippet": "The report summarizes adoption.", "credibility": {"score": 0.6}},
            ],
            "answer": "Quarterly adoption was 10 in Q1, 14 in Q2, and 18 in Q3.",
        }
    )

    assert state["artifact"]["type"] == "chart"
    assert [point["label"] for point in state["artifact"]["data"]] == ["Q1", "Q2", "Q3"]
    assert [point["value"] for point in state["artifact"]["data"]] == [10, 14, 18]


@pytest.mark.asyncio
async def test_output_router_refines_ambiguous_text_to_table(monkeypatch):
    async def fake_classify_output_with_llm(query, findings, answer, signals):
        assert signals["source_count"] == 5
        assert signals["comparative_finding_count"] >= 5
        return "table"

    monkeypatch.setattr(
        "backend.nodes.output_router._classify_output_with_llm",
        fake_classify_output_with_llm,
    )

    findings = [
        {
            "title": f"Vendor {index} comparison",
            "url": f"https://example.com/{index}",
            "snippet": "Comparison of features, price, and support tradeoffs across options.",
            "credibility": {"score": 0.7 + index / 100},
        }
        for index in range(5)
    ]

    state = await output_router_node(
        {
            "query": "Which vendor is best for our workflow?",
            "output_type": "text",
            "findings": findings,
            "answer": "The answer compares vendors by features, support, and price.",
        }
    )

    assert state["output_type"] == "table"
    assert state["artifact"]["type"] == "table"
    assert len(state["artifact"]["rows"]) == 5


@pytest.mark.asyncio
async def test_output_router_keeps_text_without_clear_structured_findings(monkeypatch):
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("late router LLM should not run without enough structure")

    monkeypatch.setattr("backend.nodes.output_router._classify_output_with_llm", fail_if_called)

    state = await output_router_node(
        {
            "query": "What happened?",
            "output_type": "text",
            "findings": [
                {"title": "Source A", "snippet": "A plain narrative update."},
                {"title": "Source B", "snippet": "Another plain narrative update."},
            ],
            "answer": "A short prose explanation is sufficient.",
        }
    )

    assert state["output_type"] == "text"
    assert state["artifact"] is None


@pytest.mark.asyncio
async def test_output_router_ignores_weak_comparative_words(monkeypatch):
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("late router LLM should not run for weak narrative triggers")

    monkeypatch.setattr("backend.nodes.output_router._classify_output_with_llm", fail_if_called)

    findings = [
        {
            "title": f"Narrative source {letter}",
            "snippet": "This explains price pressure, product features, and vendor choices without contrasting alternatives.",
        }
        for letter in ["A", "B", "C", "D", "E"]
    ]

    state = await output_router_node(
        {
            "query": "Why did the price change?",
            "output_type": "text",
            "findings": findings,
            "answer": "The answer is a narrative explanation of causes and context.",
        }
    )

    assert state["output_type"] == "text"
    assert state["artifact"] is None


@pytest.mark.asyncio
async def test_output_router_ignores_numeric_query_terms_without_structured_findings(monkeypatch):
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("late router LLM should not run for numeric query terms alone")

    monkeypatch.setattr("backend.nodes.output_router._classify_output_with_llm", fail_if_called)

    findings = [
        {
            "title": f"CRM source {letter}",
            "snippet": "This source describes CRM plan packaging and buying context.",
            "query": "How do the top 3 CRM platforms differ in pricing?",
        }
        for letter in ["A", "B", "C", "D", "E"]
    ]

    state = await output_router_node(
        {
            "query": "How do the top 3 CRM platforms differ in pricing?",
            "output_type": "text",
            "findings": findings,
            "answer": "The answer describes CRM pricing plan context.",
        }
    )

    assert state["output_type"] == "text"
    assert state["artifact"] is None


@pytest.mark.asyncio
async def test_output_router_refines_differ_query_when_findings_corroborate(monkeypatch):
    async def fake_classify_output_with_llm(query, findings, answer, signals):
        assert signals["comparative_finding_count"] == 2
        assert signals["answer_has_comparative"] is True
        return "table"

    monkeypatch.setattr(
        "backend.nodes.output_router._classify_output_with_llm",
        fake_classify_output_with_llm,
    )

    findings = [
        {
            "title": "CRM source A",
            "snippet": "This comparison weighs CRM pricing, support, and automation limits.",
            "credibility": {"score": 0.8},
        },
        {
            "title": "CRM source B",
            "snippet": "The platforms have different plan bundles and upgrade paths.",
            "credibility": {"score": 0.8},
        },
        {
            "title": "CRM source C",
            "snippet": "Plan pages describe seats, contact limits, and included tools.",
            "credibility": {"score": 0.8},
        },
        {
            "title": "CRM source D",
            "snippet": "Small teams consider integrations, billing model, and implementation work.",
            "credibility": {"score": 0.8},
        },
        {
            "title": "CRM source E",
            "snippet": "Pricing pages describe free, starter, professional, and enterprise plans.",
            "credibility": {"score": 0.8},
        },
    ]

    state = await output_router_node(
        {
            "query": "How do the top 3 CRM platforms differ in pricing?",
            "output_type": "text",
            "findings": findings,
            "answer": "The answer compares how CRM platforms differ by pricing tiers and included capabilities.",
        }
    )

    assert state["output_type"] == "table"
    assert state["artifact"]["type"] == "table"


@pytest.mark.asyncio
async def test_output_router_late_llm_uses_json_fallback_and_validation(monkeypatch):
    class FakeClient:
        async def chat(self, messages, **kwargs):
            return 'Sure: {"output_type": "chart"}'

    monkeypatch.setattr("backend.nodes.output_router.OllamaClient", lambda: FakeClient())

    output_type = await _classify_output_with_llm(
        query="Show the revenue trend",
        findings=[{"title": "Metric source", "snippet": "Revenue increased 12%."}],
        answer="Revenue increased 12%.",
        signals={
            "source_count": 5,
            "numeric_finding_count": 5,
            "comparative_finding_count": 0,
            "answer_has_numeric": True,
            "answer_has_comparative": False,
        },
    )

    assert output_type == "chart"


@pytest.mark.asyncio
async def test_output_router_late_llm_rejects_invalid_output_type(monkeypatch):
    class FakeClient:
        async def chat(self, messages, **kwargs):
            return '{"output_type": "slides"}'

    monkeypatch.setattr("backend.nodes.output_router.OllamaClient", lambda: FakeClient())

    output_type = await _classify_output_with_llm(
        query="Show the revenue trend",
        findings=[{"title": "Metric source", "snippet": "Revenue increased 12%."}],
        answer="Revenue increased 12%.",
        signals={
            "source_count": 5,
            "numeric_finding_count": 5,
            "comparative_finding_count": 0,
            "answer_has_numeric": True,
            "answer_has_comparative": False,
        },
    )

    assert output_type is None
