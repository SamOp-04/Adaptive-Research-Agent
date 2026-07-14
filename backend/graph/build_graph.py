from __future__ import annotations

import inspect
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from backend.graph.state import OutputType, ResearchState, initial_state
from backend.nodes.intent_classifier import classify_intent
from backend.nodes.output_router import output_router_node
from backend.nodes.planner import planner_node
from backend.nodes.research import research_node
from backend.nodes.synthesis import synthesis_node
from backend.sse.events import make_step_event


Node = Callable[[ResearchState], ResearchState | Awaitable[ResearchState] | dict[str, Any]]

NODE_SEQUENCE: list[tuple[str, str, Node]] = [
    ("intent", "Classifying intent", classify_intent),
    ("planning", "Planning research", planner_node),
    ("research", "Searching sources", research_node),
    ("synthesis", "Synthesizing findings", synthesis_node),
    ("output", "Routing output", output_router_node),
]


async def _call_node(node: Node, state: ResearchState) -> dict[str, Any]:
    result = node(state)
    if inspect.isawaitable(result):
        result = await result
    return dict(result or {})


async def stream_research_graph(
    query: str,
    *,
    session_id: str | None = None,
    output_type: OutputType | None = None,
) -> AsyncIterator[dict[str, Any]]:
    state = initial_state(query, session_id=session_id, output_type=output_type)

    for step, message, node in NODE_SEQUENCE:
        started = make_step_event(step, "running", message)
        state["events"].append(started)
        yield started

        try:
            state.update(await _call_node(node, state))
            completed = make_step_event(step, "completed", f"{message} complete")
        except Exception as exc:  # pragma: no cover - live stream guard
            state.setdefault("errors", []).append(str(exc))
            completed = make_step_event(step, "failed", str(exc))

        state["events"].append(completed)
        yield completed

    yield make_step_event(
        "complete",
        "completed",
        "Research complete",
        payload={
            "session_id": state.get("session_id"),
            "answer": state.get("answer"),
            "output_type": state.get("output_type"),
            "artifact": state.get("artifact"),
            "sources": state.get("findings", []),
            "errors": state.get("errors", []),
        },
    )


async def run_research_graph(
    query: str,
    *,
    session_id: str | None = None,
    output_type: OutputType | None = None,
) -> ResearchState:
    state = initial_state(query, session_id=session_id, output_type=output_type)

    for step, message, node in NODE_SEQUENCE:
        state["events"].append(make_step_event(step, "running", message))
        try:
            state.update(await _call_node(node, state))
            state["events"].append(make_step_event(step, "completed", f"{message} complete"))
        except Exception as exc:
            state.setdefault("errors", []).append(str(exc))
            state["events"].append(make_step_event(step, "failed", str(exc)))
            break

    return state


def build_graph():
    """Return a compiled LangGraph graph when the dependency is available."""
    from langgraph.graph import END, StateGraph

    graph = StateGraph(ResearchState)
    graph.add_node("intent", classify_intent)
    graph.add_node("planning", planner_node)
    graph.add_node("research", research_node)
    graph.add_node("synthesis", synthesis_node)
    graph.add_node("output", output_router_node)
    graph.set_entry_point("intent")
    graph.add_edge("intent", "planning")
    graph.add_edge("planning", "research")
    graph.add_edge("research", "synthesis")
    graph.add_edge("synthesis", "output")
    graph.add_edge("output", END)
    return graph.compile()
