from __future__ import annotations

from backend.graph.state import ResearchState


def planner_node(state: ResearchState) -> ResearchState:
    query = state.get("query", "").strip()
    depth = state.get("depth", "standard")
    query_type = state.get("query_type", "exploratory")

    if depth == "quick":
        sub_questions = [query]
    elif depth == "deep":
        sub_questions = [
            query,
            f"What is the recent evidence about {query}?",
            f"What are the strongest counterpoints or limitations around {query}?",
            f"What reputable sources provide data about {query}?",
            f"What practical implications or next steps follow from {query}?",
        ]
    elif query_type == "comparative":
        sub_questions = [
            query,
            f"What criteria are most useful for comparing {query}?",
            f"What reputable data sources compare {query}?",
        ]
    else:
        sub_questions = [
            query,
            f"What are the latest reputable findings about {query}?",
            f"What context or tradeoffs matter for {query}?",
        ]

    return {"sub_questions": [item for item in sub_questions if item]}
