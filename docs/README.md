# Adaptive Research Agent v1.2

This scaffold contains a FastAPI backend and a Next.js frontend for an adaptive research assistant.

## Backend

- `backend/main.py` exposes health, JSON chat, and SSE chat endpoints.
- `backend/graph/` contains the agent state schema and graph runner.
- `backend/nodes/` contains LLM-first intent/output-type classification, planning, research, synthesis, and output routing nodes.
- `backend/skills/` contains source scoring, web search wrappers, and document generation orchestration.
- `backend/files/` contains DOCX and PDF generation helpers.
- `backend/db/` contains SQLAlchemy setup and session/message models.

## Pipeline

The graph chooses the response format before research starts. The intent classifier reads the raw user request, calls the configured Ollama model, and sets `query_type`, `depth`, and `output_type`. If the LLM classification fails, a keyword heuristic is used as a fallback.

The later output router builds the final artifact for the selected `output_type`: text, chart, table, DOCX, or PDF. It preserves explicit non-text requests, but when the early classifier left the format as default `text` and the retrieved findings have clear numeric or comparative structure, it runs one cheap JSON-only LLM check against the findings and synthesized answer. That late check can upgrade ambiguous text output to a chart or table while avoiding format flip-flopping for explicit requests.

Run locally:

```bash
python -m venv backend/.venv
backend/.venv/Scripts/pip install -r backend/requirements.txt
backend/.venv/Scripts/uvicorn backend.main:app --reload
```

### PDF generation on Windows

WeasyPrint needs native Pango/GObject DLLs in addition to the Python package. Install them with MSYS2:

```bash
C:\msys64\usr\bin\pacman.exe -S --needed mingw-w64-x86_64-pango
```

The backend automatically looks in `C:\msys64\mingw64\bin` before importing WeasyPrint. For direct CLI use, launch with that directory on `PATH`.

For Ollama Cloud, put these in `backend/.env`:

```bash
OLLAMA_API_KEY=your_api_key
OLLAMA_HOST=https://ollama.com
OLLAMA_MODEL=gpt-oss:120b
```

If `OLLAMA_API_KEY` is set and the host is blank or still pointed at localhost, the backend automatically uses `https://ollama.com`.

## Frontend

- `frontend/app/page.tsx` renders the chat workspace.
- `frontend/app/api/chat/route.ts` proxies JSON and SSE calls to FastAPI.
- `frontend/components/` contains chat, step trace, artifact, and download UI.
- `frontend/lib/` contains fetch and SSE helpers.
- `frontend/types/agent.ts` defines shared frontend agent types.

Run locally:

```bash
cd frontend
npm install
npm run dev
```

By default, the frontend expects the backend at `http://127.0.0.1:8000`. Override with `BACKEND_URL` when needed.
