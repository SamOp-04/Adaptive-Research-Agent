from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any

from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from backend.config.settings import get_settings

logger = logging.getLogger(__name__)

SEARCH_TIMEOUT_SECONDS = 20
DUCKDUCKGO_TIMEOUT_SECONDS = 8
DUCKDUCKGO_BACKENDS = ("api", "html", "lite")


@dataclass(slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    published_at: str | None = None
    citations: int = 0


async def search_web(query: str, *, max_results: int = 5) -> list[SearchResult]:
    settings = get_settings()
    providers: list[tuple[str, Any]] = []

    if settings.tavily_api_key:
        providers.append(("tavily", _tavily_search))
    providers.append(("duckduckgo", _duckduckgo_search))

    for provider_name, provider in providers:
        try:
            results = await asyncio.wait_for(
                asyncio.to_thread(provider, query, max_results),
                timeout=SEARCH_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            logger.warning(
                "Search provider %s failed for query %r: %s",
                provider_name,
                query,
                _describe_search_error(exc),
            )
            continue

        if results:
            return results

        logger.warning("Search provider %s returned no usable results for query %r", provider_name, query)

    return []


@retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=4), stop=stop_after_attempt(3), reraise=True)
def _tavily_search(query: str, max_results: int) -> list[SearchResult]:
    from tavily import TavilyClient

    api_key = get_settings().tavily_api_key or os.environ["TAVILY_API_KEY"]
    client = TavilyClient(api_key=api_key)
    response: dict[str, Any] = client.search(
        query=query,
        max_results=max_results,
        search_depth="advanced",
        include_answer=False,
        include_raw_content=False,
    )
    return [
        SearchResult(
            title=item.get("title", ""),
            url=item.get("url", ""),
            snippet=item.get("content", ""),
            published_at=item.get("published_date"),
        )
        for item in response.get("results", [])
        if item.get("url")
    ]


@retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=4), stop=stop_after_attempt(2), reraise=True)
def _duckduckgo_search(query: str, max_results: int) -> list[SearchResult]:
    try:
        from duckduckgo_search import DDGS
    except Exception:
        return []

    last_error: Exception | None = None
    for backend in DUCKDUCKGO_BACKENDS:
        try:
            results: list[SearchResult] = []
            with DDGS(timeout=DUCKDUCKGO_TIMEOUT_SECONDS) as ddgs:
                for item in ddgs.text(query, backend=backend, max_results=max_results):
                    results.append(
                        SearchResult(
                            title=item.get("title", ""),
                            url=item.get("href", ""),
                            snippet=item.get("body", ""),
                        )
                    )

            filtered = [item for item in results if item.url]
            if filtered:
                return filtered
        except Exception as exc:
            last_error = exc
            logger.info(
                "DuckDuckGo backend %s failed for query %r: %s",
                backend,
                query,
                _describe_search_error(exc),
            )

    if last_error is not None:
        raise last_error
    return []


def _describe_search_error(exc: Exception) -> str:
    if isinstance(exc, RetryError):
        last_exception = exc.last_attempt.exception()
        if last_exception is not None:
            exc = last_exception

    return f"{type(exc).__name__}: {exc}"
