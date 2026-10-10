<div align="center">

<img src="frontend/public/logo_w_text.png" alt="Adaptive Research Agent" width="320" />

### An AI research assistant that decides *how* to answer before it starts researching

Ask a question. The agent classifies your intent, plans sub-questions, searches the web, scores every source for credibility, and delivers the answer in the format that fits: **text, chart, table, DOCX or PDF**, with a live trace of every step.

<p>
  <img alt="Next.js" src="https://img.shields.io/badge/Next.js-14-000000?logo=nextdotjs&logoColor=white" />
  <img alt="React" src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black" />
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white" />
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" />
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" />
  <img alt="Postgres" src="https://img.shields.io/badge/Postgres-Supabase%20%7C%20Neon-4169E1?logo=postgresql&logoColor=white" />
  <img alt="Ollama" src="https://img.shields.io/badge/LLM-Ollama-111111?logo=ollama&logoColor=white" />
  <img alt="Deploy" src="https://img.shields.io/badge/Deploy-Vercel-000000?logo=vercel&logoColor=white" />
  <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-green.svg" />
</p>

</div>

---

## Table of contents

- [Why this project](#why-this-project)
- [Features](#features)
- [Architecture](#architecture)
- [How a request flows](#how-a-request-flows)
- [Source credibility scoring](#source-credibility-scoring)
- [Output types](#output-types)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [API reference](#api-reference)
- [Deploying to Vercel](#deploying-to-vercel)
- [Testing](#testing)
- [Known limitations](#known-limitations)
- [Roadmap](#roadmap)

---

## Why this project

Most research chatbots return a wall of text, whatever you asked for. This agent treats the **shape of the answer** as part of the problem:

- A comparison becomes a **table**.
- A numeric trend becomes a **chart**.
- A request for a shareable brief becomes a **DOCX or PDF** you can download.
- A quick factual question stays a short **text** answer.

It also refuses to treat every search result equally. Each source is scored for credibility and topical relevance, and low-quality or off-topic results are filtered out before the model ever sees them.

## Features

| | |
|---|---|
| **Intent-first routing** | An LLM classifier reads the raw request and sets `query_type`, `depth` and `output_type` before any research happens. A keyword heuristic is the fallback if the LLM call fails. |
| **Adaptive research depth** | `quick`, `standard` and `deep` modes change how many sub-questions are planned and how many results are fetched per question. |
| **Credibility-aware retrieval** | Domain tiers, recency decay, a blocklist, URL de-duplication and a topical-relevance gate. |
| **Grounded synthesis** | Prompts forbid inventing statistics, quotes or tool names that are not in the retrieved findings. |
| **Smart output upgrades** | If the answer was left as plain text but the findings are clearly numeric or comparative, a cheap JSON-only LLM check can upgrade it to a chart or table. Explicit user choices are never overridden. |
| **Live agent trace** | Every pipeline step streams to the UI over Server-Sent Events, so you can watch the agent work. |
| **Persistent sessions** | Conversations and artifacts are stored in a database, and follow-up questions use recent chat context. |
| **Downloadable reports** | DOCX and PDF generation with sources and key findings. |
| **Fallback everywhere** | Tavily falls back to DuckDuckGo, PDF falls back to DOCX where the PDF engine is unavailable, and synthesis falls back to a ranked source summary if the LLM returns nothing. |

## Architecture

![Architecture diagram](docs/architecture-diagram.png)

The same system, in more detail:

```mermaid
flowchart LR
    subgraph Client["Browser"]
        UI["Next.js 14 chat UI<br/>ChatWindow, StepTrace, Artifacts"]
    end

    subgraph FE["Next.js server (Vercel project 1)"]
        PROXY["API route handlers<br/>/api/chat, /api/sessions, /files"]
    end

    subgraph BE["FastAPI backend (Vercel project 2)"]
        API["main.py<br/>/chat, /chat/stream, /sessions"]
        subgraph PIPE["Research pipeline"]
            direction TB
            N1["1. Intent classifier"] --> N2["2. Planner"]
            N2 --> N3["3. Research"]
            N3 --> N4["4. Synthesis"]
            N4 --> N5["5. Output router"]
        end
        SK["Skills<br/>web search, credibility,<br/>chart extraction, text cleanup"]
        FILES["File generators<br/>DOCX / PDF"]
    end

    DB[("Postgres<br/>Supabase or Neon<br/>SQLite locally")]
    LLM["Ollama<br/>Cloud or local"]
    SEARCH["Tavily<br/>DuckDuckGo fallback"]

    UI -- "SSE + JSON" --> PROXY
    PROXY -- "server-side fetch" --> API
    API --> PIPE
    PIPE --> SK
    SK --> SEARCH
    N1 & N4 & N5 --> LLM
    N5 --> FILES
    API <--> DB
```

**Design decisions worth knowing**

- **The browser never talks to the backend directly.** All calls go through Next.js route handlers that proxy to FastAPI. This removes the need for CORS in production and keeps the backend URL out of client code.
- **Format is chosen early.** The output type is decided before research, which lets synthesis tailor its prompt to the target format (for example, writing report-style prose for DOCX/PDF).
- **Streaming first.** The UI uses the `/chat/stream` SSE endpoint. A blocking `/chat` JSON endpoint also exists for simple clients and tests.
- **Skills are separated from routing.** The router decides *what* artifact to build. The design docs in `backend/skills/` (`DESIGN.md` plus one file per output type) define *how* it should look, so every artifact shares the same tokens.

## How a request flows

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant FE as Next.js (proxy)
    participant API as FastAPI
    participant LLM as Ollama
    participant WEB as Tavily / DuckDuckGo
    participant DB as Postgres

    U->>FE: Ask a question
    FE->>API: GET /chat/stream?q=...
    API->>DB: Load last 8 messages for context
    API-->>U: step: intent (running)
    API->>LLM: Classify intent
    LLM-->>API: needs_research, query_type, depth, output_type
    alt needs_research = true
        API-->>U: step: planning
        API->>API: Build 1 to 5 sub-questions
        API-->>U: step: research
        loop each sub-question
            API->>WEB: Search
            WEB-->>API: Results
            API->>API: Score credibility, check relevance, de-duplicate
        end
    end
    API-->>U: step: synthesis
    API->>LLM: Write grounded answer from findings
    API-->>U: step: output
    API->>LLM: Optional late format check and chart extraction
    API->>API: Build chart / table / DOCX / PDF artifact
    API->>DB: Persist user and assistant messages
    API-->>U: complete: answer, artifact, sources
```

Greetings, thanks and simple capability questions skip planning and research entirely (`needs_research = false`) and go straight to synthesis.

### Depth modes

| Depth | Sub-questions | Results per sub-question | Triggered by |
|---|---|---|---|
| `quick` | 1 | 3 | Short factual asks, or words like *brief*, *summary*, *tl;dr* |
| `standard` | 3 | 5 | Default |
| `deep` | 5 (evidence, counterpoints, data sources, implications) | 8 | Words like *comprehensive*, *deep*, *literature review* |

## Source credibility scoring

Every result gets a score between 0 and 1, computed in `backend/skills/source_evaluation.py` and configured in `backend/config/source_credibility.json`.

```
score = 0.6 × domain tier  +  0.3 × recency  +  0.1 × domain match
```

| Domain tier | Score | Examples |
|---|---|---|
| High | 0.95 | `nature.com`, `nih.gov`, `who.int`, `worldbank.org`, `arxiv.org`, any `.gov` / `.edu` |
| Medium | 0.72 | `reuters.com`, `apnews.com`, `ft.com`, `bloomberg.com`, `gartner.com` |
| Low | 0.42 | `medium.com`, `substack.com`, `wikipedia.org`, `reddit.com` |
| Unknown | 0.55 | Anything not listed |
| Blocklist | 0 | `pinterest.com`, `quora.com` |

- **Recency** decays linearly over 540 days. Sources with no date get a neutral 0.5.
- **Minimum threshold:** results scoring below **0.35** are dropped.
- **Topical relevance** is checked separately. A trusted domain is not automatically relevant, so a `.gov` page about an unrelated topic will not pass.
- **De-duplication** keeps the highest-scoring copy of each URL.

In the UI each source shows a three-state badge: **High** (≥ 0.75), **Medium** (0.5 to 0.74), **Low** (< 0.5). Low credibility is shown in neutral gray, never red, because red is reserved for real errors.

## Output types

| `output_type` | What the user gets | Built by |
|---|---|---|
| `text` | Short or long markdown answer with citations | Synthesis node |
| `chart` | Interactive Recharts visualization from numbers extracted and validated against the sources | `chart_extraction.py` + `ChartArtifact.tsx` |
| `table` | Sortable table for comparisons and rankings | `TableArtifact.tsx` (TanStack Table) |
| `docx` | Downloadable Word report with key findings and sources | `files/docx_generator.py` |
| `pdf` | Downloadable styled PDF report | `files/pdf_generator.py` (WeasyPrint) |

## Tech stack

**Frontend:** Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Recharts, TanStack Table, react-markdown with remark-gfm, react-syntax-highlighter, lucide-react.

**Backend:** FastAPI, Pydantic v2, SQLAlchemy 2 (async), sse-starlette, python-docx, tenacity for retries.

**AI and retrieval:** Ollama (Ollama Cloud or a local model), Tavily search with DuckDuckGo fallback, LangGraph definition of the pipeline.

**Data:** SQLite for local development, hosted Postgres (Supabase or Neon) in production via `asyncpg`.

**Hosting:** Vercel for both the frontend and the backend.

## Project structure

```
Adaptive-Research-Agent/
├── main.py                      # Vercel entrypoint shim: exposes backend.main:app
├── vercel.json                  # Backend function config (bundle + max duration)
├── requirements.txt             # Production dependencies (Vercel installs these)
├── requirements-dev.txt         # Local extras: uvicorn, aiosqlite, WeasyPrint, pytest
├── backend/
│   ├── main.py                  # FastAPI app, routes, lifespan, file cleanup
│   ├── config/
│   │   ├── settings.py          # Pydantic settings, Ollama host/model resolution
│   │   └── source_credibility.json
│   ├── graph/
│   │   ├── state.py             # ResearchState, OutputType, StepEvent types
│   │   └── build_graph.py       # Step runner (streaming) + LangGraph definition
│   ├── nodes/
│   │   ├── intent_classifier.py # LLM classification + heuristic fallback
│   │   ├── planner.py           # Sub-question planning by depth and query type
│   │   ├── research.py          # Search, score, relevance gate, de-duplicate
│   │   ├── synthesis.py         # Grounded answer + key findings
│   │   └── output_router.py     # Final format decision and artifact builder
│   ├── skills/
│   │   ├── web_research.py      # Tavily + DuckDuckGo with retries and timeouts
│   │   ├── source_evaluation.py # Credibility scoring
│   │   ├── chart_extraction.py  # Numeric extraction and validation for charts
│   │   ├── document_generation.py
│   │   ├── DESIGN.md            # Shared design tokens
│   │   └── design-skills/       # Per-output-type design rules
│   ├── files/                   # DOCX, PDF and markdown rendering helpers
│   ├── llm/ollama_client.py     # Async Ollama client and prompts
│   ├── db/                      # Async engine, session factory, models
│   ├── sse/events.py            # Step event and SSE payload helpers
│   └── tests/                   # pytest suite
├── frontend/
│   ├── app/
│   │   ├── api/chat/route.ts    # SSE + JSON proxy to the backend
│   │   ├── api/sessions/        # Session list and message history proxies
│   │   └── files/[fileName]/    # Download proxy for generated documents
│   ├── components/              # ChatWindow, MessageBubble, StepTrace, artifacts
│   ├── lib/                     # fetch and EventSource helpers
│   └── types/agent.ts           # Shared types
└── docs/                        # Architecture diagram and logo
```

## Getting started

### Prerequisites

- Python 3.11 or newer (3.12 recommended)
- Node.js 18 or newer
- An Ollama setup: an [Ollama Cloud](https://ollama.com) API key, or a local Ollama server with a model pulled
- Optional: a [Tavily](https://tavily.com) API key for higher-quality search (DuckDuckGo is used otherwise)

### 1. Clone and install the backend

```bash
git clone https://github.com/SamOp-04/Adaptive-Research-Agent.git
cd Adaptive-Research-Agent

python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements-dev.txt
```

### 2. Configure the backend

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:

```dotenv
TAVILY_API_KEY=your_tavily_key          # optional
OLLAMA_API_KEY=your_ollama_cloud_key    # leave empty for a local Ollama server
OLLAMA_HOST=https://ollama.com          # or http://localhost:11434
OLLAMA_MODEL=gpt-oss:120b
DATABASE_URL=sqlite+aiosqlite:///./adaptive_research_agent.db
```

### 3. Run the backend (from the repo root)

```bash
uvicorn backend.main:app --reload --port 8000
```

Check it: <http://127.0.0.1:8000/health> should return `{"status":"ok"}`.

> Run it from the **repo root** as `backend.main:app`. Running `uvicorn main:app` from inside `backend/` fails because the code imports modules as `backend.*`.

### 4. Run the frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open <http://localhost:3000>.

### Local PDF export

PDF generation uses WeasyPrint, which needs native Pango libraries.

- **macOS:** `brew install pango`
- **Ubuntu / Debian:** `sudo apt install libpango-1.0-0 libpangoft2-1.0-0`
- **Windows:** install through MSYS2, then the backend finds the DLLs automatically:
  ```bash
  C:\msys64\usr\bin\pacman.exe -S --needed mingw-w64-x86_64-pango
  ```

## Configuration

### Backend (`backend/.env` locally, Vercel Environment Variables in production)

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | Local: `sqlite+aiosqlite:///./adaptive_research_agent.db`. Production: your Postgres URL (see below). |
| `OLLAMA_API_KEY` | For Ollama Cloud | If set while the host is blank or localhost, the app switches to `https://ollama.com` automatically. |
| `OLLAMA_HOST` | No | Defaults to `http://localhost:11434`, or `https://ollama.com` when an API key is set. |
| `OLLAMA_MODEL` | No | Defaults to `gpt-oss:120b` with an API key, otherwise `qwen2.5:14b-instruct-q4_K_M`. |
| `TAVILY_API_KEY` | No | Enables Tavily search. Without it the app uses DuckDuckGo only. |

**Postgres URL format.** You can paste the connection string straight from Supabase or Neon. The backend rewrites `postgres://` and `postgresql://` to `postgresql+asyncpg://`, maps `sslmode` to `ssl`, and drops `channel_binding`. Add `?ssl=require` if your provider's string has no SSL parameter:

```dotenv
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/postgres?ssl=require
```

> On Supabase, use the **Session pooler** string (`...pooler.supabase.com:5432`). The direct `db.<ref>.supabase.co` host is IPv6-only on the free tier and often unreachable from serverless platforms. URL-encode special characters in the password, or use a password with letters and numbers only.

### Frontend (`frontend/.env` locally, Vercel Environment Variables in production)

| Variable | Required | Description |
|---|---|---|
| `BACKEND_URL` | Yes in production | Base URL of the FastAPI deployment, with no trailing slash. Defaults to `http://127.0.0.1:8000`. |

## API reference

### Backend (FastAPI)

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check. Returns `{"status":"ok"}`. |
| `POST` | `/chat` | Blocking chat. Body: `{ "message", "session_id?", "output_type?" }`. Returns answer, artifact, sources, steps and errors. |
| `GET` | `/chat/stream` | SSE chat. Query: `q`, `session_id?`, `output_type?`. Streams `step` events. |
| `GET` | `/sessions` | The 50 most recent sessions. |
| `GET` | `/sessions/{session_id}/messages` | Message history for a session. |
| `GET` | `/files/{file_name}` | Download a generated DOCX or PDF. |

Interactive docs are available at `/docs` (Swagger UI) when the backend is running.

### Streaming events

Every event has the SSE event name `step` and a JSON body:

```json
{
  "step": "research",
  "status": "running",
  "message": "Searching sources",
  "payload": {},
  "timestamp": "2026-10-11T08:30:12.345+00:00"
}
```

`step` is one of `intent`, `planning`, `research`, `synthesis`, `output`, then a final `complete` event whose `payload` contains `session_id`, `answer`, `output_type`, `artifact`, `sources` and `errors`. `status` is `running`, `completed` or `failed`.

### Artifact shapes

```ts
type Artifact =
  | { type: "chart"; data: Array<Record<string, string | number>> }
  | { type: "table"; columns?: string[]; rows: Array<Record<string, unknown>> }
  | { type: "docx" | "pdf"; href: string; fileName?: string }
  | null;
```

## Deploying to Vercel

The repo deploys as **two Vercel projects** from the same GitHub repository.

### Backend project (repo root)

1. Import the repo. Set **Root Directory** to the repo root (leave it blank).
2. Set **Framework Preset** to *Other*. Leave **Build Command**, **Output Directory** and **Install Command** empty, so Vercel installs `requirements.txt` itself and can optimize the bundle.
3. Add environment variables: `DATABASE_URL`, `OLLAMA_API_KEY`, `OLLAMA_HOST`, `OLLAMA_MODEL`, and optionally `TAVILY_API_KEY`.
4. Deploy, then verify:
   ```bash
   curl -i https://<your-backend>.vercel.app/health
   curl -i https://<your-backend>.vercel.app/sessions    # expect 200 and []
   ```

The root `main.py` re-exports `backend.main:app` so Vercel's FastAPI detection finds it, and `vercel.json` makes sure the `backend/` folder is bundled. Tables are created automatically on startup.

### Frontend project (`frontend/`)

1. Import the same repo as a second project. Set **Root Directory** to `frontend`.
2. Add `BACKEND_URL` set to the backend deployment URL.
3. Deploy.

### Serverless behavior to be aware of

- **Read-only filesystem.** Only `/tmp` is writable, so generated files go to `/tmp/generated_files` when running on Vercel.
- **PDF export.** WeasyPrint needs system libraries that Vercel does not provide. On Vercel, a PDF request automatically falls back to a DOCX file. For real PDFs, host the backend on a platform that allows system packages (Render, Railway, Fly.io) or switch to a pure-Python PDF library.
- **Generated files are ephemeral.** A download request can land on a different instance than the one that created the file. For durable downloads, upload files to object storage (Vercel Blob, S3 or Supabase Storage) and return that URL.
- **Long-running requests.** Research streams over SSE and calls an LLM, so both the backend function and the frontend chat route set `maxDuration = 300`. The maximum your plan allows may be lower.

## Testing

```bash
# from the repo root, with requirements-dev.txt installed
pytest backend/tests -q
```

The suite covers intent classification, credibility scoring, the research node, synthesis, chart extraction, output routing, document generation, and sessions with graph execution.

## Known limitations

- Answer quality depends on the configured Ollama model and on what the search providers return. DuckDuckGo results are less reliable than Tavily.
- Chart extraction only produces charts when the sources contain clearly comparable numbers. Otherwise the answer stays text or becomes a table.
- There is no user authentication yet, so sessions are shared across all visitors of a deployment.
- Credibility tiers are a curated allow and deny list, not a live reputation service.

## Roadmap

- [ ] User accounts and per-user session history
- [ ] Durable file storage for generated reports
- [ ] Pure-Python PDF engine for serverless hosting
- [ ] Per-claim citations linking sentences to sources
- [ ] Configurable credibility tiers from the UI
- [ ] Optional additional search providers

## License

Released under the [MIT License](LICENSE).

---

<div align="center">
Built with FastAPI, Next.js and Ollama.
</div>
