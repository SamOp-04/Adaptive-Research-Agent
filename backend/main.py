from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from time import time

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from sse_starlette.sse import EventSourceResponse
except ImportError:  # pragma: no cover - local dev fallback before requirements are installed
    from fastapi.responses import StreamingResponse

    class EventSourceResponse(StreamingResponse):
        def __init__(self, content, *args, **kwargs):
            async def encode_events():
                async for event in content:
                    event_name = event.get("event", "message")
                    data = event.get("data", "")
                    yield f"event: {event_name}\ndata: {data}\n\n"

            super().__init__(encode_events(), media_type="text/event-stream", *args, **kwargs)

from backend.db.database import get_db, init_db
from backend.db.models import Message, Session
from backend.graph.build_graph import run_research_graph, stream_research_graph
from backend.graph.state import OutputType
from backend.skills.document_generation import GENERATED_FILES_DIR
from backend.sse.events import to_sse_payload


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    GENERATED_FILES_DIR.mkdir(parents=True, exist_ok=True)
    _cleanup_generated_files()
    yield


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    output_type: OutputType | None = None


app = FastAPI(
    title="Adaptive Research Agent",
    version="1.2.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GENERATED_FILES_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(GENERATED_FILES_DIR)), name="files")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    conversation_context = await _recent_session_context(db, request.session_id)
    state = await run_research_graph(
        request.message,
        session_id=request.session_id,
        output_type=request.output_type,
        conversation_context=conversation_context,
    )
    await _persist_chat_turn(db, request.message, state)
    return {
        "session_id": state.get("session_id"),
        "answer": state.get("answer"),
        "output_type": state.get("output_type"),
        "artifact": state.get("artifact"),
        "sources": state.get("findings", []),
        "steps": state.get("events", []),
        "errors": state.get("errors", []),
    }


@app.get("/chat/stream")
async def chat_stream(
    q: str,
    session_id: str | None = None,
    output_type: OutputType | None = None,
    db: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    conversation_context = await _recent_session_context(db, session_id)

    async def events():
        async for event in stream_research_graph(
            q,
            session_id=session_id,
            output_type=output_type,
            conversation_context=conversation_context,
        ):
            if event.get("step") == "complete":
                payload = event.get("payload")
                if isinstance(payload, dict):
                    await _persist_chat_turn(db, q, payload)
            yield to_sse_payload(event)

    return EventSourceResponse(events())


@app.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str, db: AsyncSession = Depends(get_db)) -> list[dict[str, object]]:
    result = await db.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    )
    return [
        {
            "id": message.id,
            "role": message.role,
            "content": message.content,
            "output_type": message.output_type,
            "artifact": message.artifact,
            "created_at": message.created_at.isoformat(),
        }
        for message in result.scalars().all()
    ]


@app.get("/sessions")
async def get_sessions(db: AsyncSession = Depends(get_db)) -> list[dict[str, object]]:
    result = await db.execute(select(Session).order_by(Session.created_at.desc()).limit(50))
    return [
        {
            "id": session.id,
            "title": session.title or "Untitled chat",
            "created_at": session.created_at.isoformat(),
        }
        for session in result.scalars().all()
    ]


async def _recent_session_context(db: AsyncSession, session_id: str | None) -> str:
    if not session_id:
        return ""

    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(8)
    )
    messages = list(reversed(result.scalars().all()))
    lines: list[str] = []
    for message in messages:
        role = "User" if message.role == "user" else "Assistant"
        content = " ".join(message.content.split())
        if content:
            lines.append(f"{role}: {content[:650]}")
    return "\n".join(lines)[-4000:]


async def _persist_chat_turn(db: AsyncSession, user_message: str, state: dict[str, object]) -> None:
    session_id = str(state.get("session_id") or "")
    if not session_id:
        return

    session = await db.get(Session, session_id)
    if session is None:
        session = Session(id=session_id, title=user_message[:255])
        db.add(session)
        await db.flush()

    db.add(Message(session_id=session_id, role="user", content=user_message))
    db.add(
        Message(
            session_id=session_id,
            role="assistant",
            content=str(state.get("answer") or ""),
            output_type=state.get("output_type"),
            artifact=state.get("artifact"),
        )
    )
    await db.commit()


def _cleanup_generated_files(*, max_age_seconds: int = 7 * 24 * 60 * 60) -> None:
    cutoff = time() - max_age_seconds
    for path in GENERATED_FILES_DIR.glob("*"):
        if not _is_generated_document(path):
            continue
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            continue


def _is_generated_document(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in {".docx", ".pdf"}
