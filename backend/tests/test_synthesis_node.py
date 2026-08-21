from __future__ import annotations

import pytest

from backend.llm.ollama_client import synthesize_with_ollama
from backend.nodes.synthesis import synthesis_node


@pytest.mark.asyncio
async def test_synthesis_node_uses_unsourced_fallback_when_search_has_no_findings(monkeypatch):
    async def fake_answer_without_sources(query: str, *, conversation_context: str = ""):
        return "Unsourced general answer."

    monkeypatch.setattr("backend.nodes.synthesis.answer_without_sources", fake_answer_without_sources)

    state = await synthesis_node({"query": "what is life", "findings": []})

    assert state["answer"] == "Unsourced general answer."
    assert state["key_findings"] == []


@pytest.mark.asyncio
async def test_synthesis_node_answers_casual_requests_without_research(monkeypatch):
    async def fake_answer_without_sources(query: str, *, conversation_context: str = ""):
        return "I am an adaptive research assistant."

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("casual requests should not synthesize research")

    monkeypatch.setattr("backend.nodes.synthesis.answer_without_sources", fake_answer_without_sources)
    monkeypatch.setattr("backend.nodes.synthesis.synthesize_with_ollama", fail_if_called)

    state = await synthesis_node({"query": "what are you", "needs_research": False})

    assert state["answer"] == "I am an adaptive research assistant."


@pytest.mark.asyncio
async def test_synthesis_node_keeps_no_results_message_when_unsourced_fallback_fails(monkeypatch):
    async def fake_answer_without_sources(query: str, *, conversation_context: str = ""):
        return None

    monkeypatch.setattr("backend.nodes.synthesis.answer_without_sources", fake_answer_without_sources)

    state = await synthesis_node({"query": "what is life", "findings": []})

    assert "I could not retrieve web results" in state["answer"]
    assert state["key_findings"] == []


@pytest.mark.asyncio
async def test_synthesis_prompt_avoids_latex_when_math_is_needed(monkeypatch):
    captured = {}

    class FakeClient:
        async def chat(self, messages, **kwargs):
            captured["messages"] = messages
            return "Plain prose answer."

    monkeypatch.setattr("backend.llm.ollama_client.OllamaClient", lambda: FakeClient())

    answer = await synthesize_with_ollama(
        "Explain transformer attention",
        [{"title": "Attention source", "snippet": "Attention uses query and key vectors.", "url": "https://example.com"}],
    )

    prompt_text = "\n".join(message["content"] for message in captured["messages"])
    assert answer == "Plain prose answer."
    assert "Do not use LaTeX" in prompt_text
    assert "simple inline code" in prompt_text
    assert "Do not add a separate Sources section" in prompt_text


@pytest.mark.asyncio
async def test_synthesis_prompt_for_pdf_writes_document_body_not_external_pdf_list(monkeypatch):
    captured = {}

    class FakeClient:
        async def chat(self, messages, **kwargs):
            captured["messages"] = messages
            return "Report body."

    monkeypatch.setattr("backend.llm.ollama_client.OllamaClient", lambda: FakeClient())

    answer = await synthesize_with_ollama(
        "Create a quantum computing PDF report",
        [{"title": "Quantum source", "snippet": "Quantum computing update.", "url": "https://example.com"}],
        output_type="pdf",
    )

    prompt_text = "\n".join(message["content"] for message in captured["messages"])
    assert answer == "Report body."
    assert "automatically generated and delivered as a downloadable file" in prompt_text
    assert "Do not recommend or link to other external documents" in prompt_text
    assert "Do not include instructions for how to build or format a Word/PDF document" in prompt_text


@pytest.mark.asyncio
async def test_synthesis_node_passes_output_type_to_synthesis(monkeypatch):
    captured = {}

    async def fake_synthesize_with_ollama(query, findings, *, output_type="text", conversation_context=""):
        captured["output_type"] = output_type
        return "Document-ready answer."

    monkeypatch.setattr("backend.nodes.synthesis.synthesize_with_ollama", fake_synthesize_with_ollama)

    state = await synthesis_node(
        {
            "query": "Make a DOCX report",
            "output_type": "docx",
            "findings": [{"title": "Source", "snippet": "Evidence."}],
        }
    )

    assert state["answer"] == "Document-ready answer."
    assert captured["output_type"] == "docx"


@pytest.mark.asyncio
async def test_synthesis_prompt_includes_conversation_context(monkeypatch):
    captured = {}

    class FakeClient:
        async def chat(self, messages, **kwargs):
            captured["messages"] = messages
            return "Context-aware answer."

    monkeypatch.setattr("backend.llm.ollama_client.OllamaClient", lambda: FakeClient())

    answer = await synthesize_with_ollama(
        "What about 2011 specifically?",
        [{"title": "Census source", "snippet": "2011 population details.", "url": "https://example.com"}],
        conversation_context="User: Tell me about Gujarat population.",
    )

    prompt_text = "\n".join(message["content"] for message in captured["messages"])
    assert answer == "Context-aware answer."
    assert "Recent conversation context" in prompt_text
    assert "Gujarat population" in prompt_text
