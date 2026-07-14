from __future__ import annotations

import os

import ollama

from backend.config.settings import get_settings
from backend.graph.state import OutputType, SourceFinding


SYNTHESIS_STYLE_INSTRUCTIONS = (
    "Do not use LaTeX or bracket-delimited math notation; express formulas in plain prose "
    "or simple inline code such as `score = (q . k) / sqrt(d_k)`."
)
DOCUMENT_OUTPUT_INSTRUCTIONS = (
    "You are writing the body content of a document that will be automatically generated "
    "and delivered as a downloadable file. Write the report itself. Do not recommend or "
    "link to other external documents. Do not include instructions for how to build or "
    "format a Word/PDF document; that step is already handled automatically."
)


class OllamaClient:
    def __init__(
        self,
        *,
        host: str | None = None,
        model: str | None = None,
    ) -> None:
        settings = get_settings()
        self.host = host or os.getenv("OLLAMA_HOST") or settings.ollama_host_url
        if settings.has_ollama_api_key and self.host.rstrip("/") in {
            "http://localhost:11434",
            "http://127.0.0.1:11434",
        }:
            self.host = "https://ollama.com"
        self.host = self.host.rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL") or settings.ollama_model_name
        self.client = ollama.AsyncClient(host=self.host, headers=settings.ollama_headers)

    async def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.2) -> str:
        response = await self.client.chat(model=self.model, messages=messages, options={"temperature": temperature})
        return response["message"]["content"]


async def synthesize_with_ollama(
    query: str,
    findings: list[SourceFinding],
    *,
    output_type: OutputType = "text",
) -> str | None:
    context = "\n".join(
        f"- {item.get('title', 'Untitled')}: {item.get('snippet', '')} Source: {item.get('url', '')}"
        for item in findings[:10]
    )
    messages = [
        {
            "role": "system",
            "content": "You synthesize web research into concise, sourced answers.",
        },
        {
            "role": "user",
            "content": (
                f"Question: {query}\n\nFindings:\n{context}\n\n"
                "Answer with clear caveats and cite source URLs inline. "
                f"{_synthesis_instructions(output_type)}"
            ),
        },
    ]
    try:
        return await OllamaClient().chat(messages)
    except Exception:
        return None


def _synthesis_instructions(output_type: OutputType) -> str:
    instructions = [SYNTHESIS_STYLE_INSTRUCTIONS]
    if output_type in {"docx", "pdf"}:
        instructions.append(DOCUMENT_OUTPUT_INSTRUCTIONS)
    return " ".join(instructions)


async def answer_without_sources(query: str) -> str | None:
    messages = [
        {
            "role": "system",
            "content": (
                "You answer concisely when live web research is unavailable. "
                "Do not invent citations, URLs, dates, statistics, or source-backed claims."
            ),
        },
        {
            "role": "user",
            "content": f"Question: {query}\n\nGive a helpful general answer and clearly state that it is unsourced.",
        },
    ]
    try:
        return await OllamaClient().chat(messages, temperature=0.3)
    except Exception:
        return None
