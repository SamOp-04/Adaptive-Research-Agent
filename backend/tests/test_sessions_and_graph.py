from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.db.database import Base
from backend.db.models import Message
from backend.graph.build_graph import run_research_graph
from backend.main import _persist_chat_turn, _recent_session_context


@pytest.mark.asyncio
async def test_persist_chat_turn_groups_messages_and_builds_recent_context():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as db:
        await _persist_chat_turn(
            db,
            "Tell me about Gujarat population.",
            {
                "session_id": "session-1",
                "answer": "Gujarat population summary.",
                "output_type": "text",
                "artifact": None,
            },
        )
        await _persist_chat_turn(
            db,
            "What about 2011 specifically?",
            {
                "session_id": "session-1",
                "answer": "The 2011 figure was included.",
                "output_type": "text",
                "artifact": None,
            },
        )

        result = await db.execute(select(Message).where(Message.session_id == "session-1"))
        messages = result.scalars().all()
        context = await _recent_session_context(db, "session-1")

    await engine.dispose()

    assert len(messages) == 4
    assert "User: Tell me about Gujarat population." in context
    assert "Assistant: Gujarat population summary." in context
    assert "User: What about 2011 specifically?" in context


@pytest.mark.asyncio
async def test_run_research_graph_continues_after_node_failure(monkeypatch):
    async def failing_node(state):
        raise RuntimeError("node failed")

    async def recovering_node(state):
        return {"answer": "Recovered answer."}

    monkeypatch.setattr(
        "backend.graph.build_graph.NODE_SEQUENCE",
        [
            ("failing", "Failing node", failing_node),
            ("recovering", "Recovering node", recovering_node),
        ],
    )

    state = await run_research_graph("test query")

    assert state["errors"] == ["node failed"]
    assert state["answer"] == "Recovered answer."
    assert [event["status"] for event in state["events"]] == [
        "running",
        "failed",
        "running",
        "completed",
    ]
