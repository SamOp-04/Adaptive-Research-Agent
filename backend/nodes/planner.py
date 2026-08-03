from __future__ import annotations

from backend.graph.state import ResearchState


def planner_node(state: ResearchState) -> ResearchState:
    query = state.get("query", "").strip()
    search_query = _query_with_context(query, state.get("conversation_context", ""))
    depth = state.get("depth", "standard")
    query_type = state.get("query_type", "exploratory")

    if depth == "quick":
        sub_questions = [search_query]
    elif depth == "deep":
        sub_questions = [
            search_query,
            f"What is the recent evidence about {search_query}?",
            f"What are the strongest counterpoints or limitations around {search_query}?",
            f"What reputable sources provide data about {search_query}?",
            f"What practical implications or next steps follow from {search_query}?",
        ]
    elif query_type == "comparative":
        sub_questions = [
            search_query,
            f"What criteria are most useful for comparing {search_query}?",
            f"What reputable data sources compare {search_query}?",
        ]
    else:
        sub_questions = [
            search_query,
            f"What are the latest reputable findings about {search_query}?",
            f"What context or tradeoffs matter for {search_query}?",
        ]

    return {"sub_questions": [item for item in sub_questions if item]}


def _query_with_context(query: str, conversation_context: str) -> str:
    context = " ".join(conversation_context.split())
    if not context:
        return query
    return f"{query} Previous conversation context: {context[:700]}"
