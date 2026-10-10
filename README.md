# The Lenny Growth Assistant

[![Tests](https://img.shields.io/badge/pytest-89%20passed%2C%200%20failed-brightgreen)](https://github.com/DineshDev812/lenny-growth-assistant)
[![Evaluation Benchmark](https://img.shields.io/badge/eval%20benchmark-20%2F20%20(100%25)-brightgreen)](https://github.com/DineshDev812/lenny-growth-assistant)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg?logo=postgresql)](https://www.postgresql.org)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg?logo=react)](https://react.dev)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20(qwen2.5%3A3b)-orange)](https://ollama.com)

A full-stack, production-grade AI assistant grounded exclusively in 300+ episodes and transcripts of **Lenny's Podcast**. Built with FastAPI, PostgreSQL full-text search, an extensible agent layer with specialized skills (Ship 30 for 30 essays, sandboxed HTML artifacts), and a modern React + Tailwind web UI.

---

## Table of Contents

- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Prerequisites](#prerequisites)
- [One-Command Quickstart](#one-command-quickstart)
- [Environment Variables](#environment-variables)
- [Model Configuration (Local Ollama & Cloud Claude)](#model-configuration)
- [Agent Skills & Claude Artifacts](#agent-skills--claude-artifacts)
- [Evaluation Suite (20 Questions, 100% Score)](#evaluation-suite)
- [Running Automated Tests](#running-automated-tests)
- [Manual UI Test Plan](#manual-ui-test-plan)
- [Troubleshooting](#troubleshooting)
- [Technical Trade-offs & Design Decisions](#technical-trade-offs)
- [Demo Video](#demo-video)

---

## Key Features

1. **Strictly Grounded Q&A**: Answers are synthesized **only** from transcript excerpts. If the corpus does not cover a topic, the assistant cleanly refuses with zero hallucinations.
2. **Deterministic Source Traceability**: Every claim carries citation tags (`[S1]`, `[S2]`) with guest names, episode titles, verbatim quotes, and **clickable YouTube deep links** (`&t=SECONDS`).
3. **Dedicated Ship 30 for 30 Essay Skill**: A purpose-built agent skill that turns transcript insights into high-engagement essays (~1,250 words, hook, narrative progression, headings, bullets, and selective bolding).
4. **Claude Artifacts-Style Split Pane**: Real-time rendering of generated Markdown and complete HTML/CSS tools side-by-side with the chat stream.
5. **Defense-in-Depth HTML Sandbox Isolation**: Generated untrusted HTML is sanitized server-side via Rust-powered `nh3` and isolated in a restricted browser iframe (`sandbox="allow-scripts"`).
6. **Zero Code Change Model Switching**: Switch between **local Ollama** (`qwen2.5:3b`) on host machine and **Anthropic Claude** purely via `.env`. Read-only provider badge visible in UI.
7. **Anonymous Cookie Sessions**: Zero-friction onboarding using HMAC-SHA256 signed `client_id` cookies and PostgreSQL session isolation.

---

## System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Web Browser Client                              │
│         (React 18 + Vite + Tailwind + Sandboxed iframe Artifacts)      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / SSE (Port 5173 / 80)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       Nginx Reverse Proxy                              │
│              (Static SPA Hosting + Streaming SSE Passthrough)          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ /api/* (Port 8000)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     FastAPI Application Layer                          │
│                                                                        │
│   API Endpoints: /api/sessions, /messages, /artifacts, /health, /meta  │
│   Middleware: Correlation ID (X-Request-ID), HMAC Cookie Auth, CORS    │
│   Agent Layer: Router, Grounding Engine, Ship 30 for 30 Skill          │
│   Sanitization: Server-side Rust nh3 HTML Cleaner                     │
│   LLM Providers: Local Ollama (qwen2.5:3b) | Anthropic Claude          │
└───────────────────┬───────────────────────────────┬────────────────────┘
                    │                               │
        SQLAlchemy  │                   HTTP Host   │ (host.docker.internal)
        AsyncPG     ▼                   Gateway     ▼
┌─────────────────────────────┐        ┌─────────────────────────────────┐
│        PostgreSQL 16        │        │     Host Machine: Ollama        │
│  - Weighted Full-Text TSV   │        │     - Model: qwen2.5:3b         │
│  - GIN Indexed Search       │        │     - 0ms cloud dependency      │
│  - Monotonic (created_at,   │        └─────────────────────────────────┘
│    seq) message ordering    │
└─────────────────────────────┘
```

---

## Prerequisites

- **Docker Desktop** (with Docker Compose v2)
- **Ollama** installed on your host machine (Windows, Mac, or Linux)
- Pull the local model (runs fast on any standard CPU, no GPU required):
  ```bash
  ollama pull qwen2.5:3b
  ```
- **Lenny's Podcast Transcripts**: Placed in `data/transcripts/episodes/{slug}/transcript.md` (mounted read-only).

---

## One-Command Quickstart

1. **Clone repository**:
   ```bash
   git clone https://github.com/DineshDev812/lenny-growth-assistant.git
   cd lenny-growth-assistant
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   ```
   *(Default `.env` is pre-configured for local Ollama with zero external keys required!)*

3. **Start local Ollama**:
   ```bash
   ollama serve
   ```

4. **Launch the Docker Compose stack**:
   ```bash
   docker compose up --build -d
   ```

5. **Open the web app**:
   Navigate to **`http://localhost:5173`** in your browser.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `MODEL_PROVIDER` | Optional | `ollama` | Active provider: `ollama` or `anthropic`. |
| `OLLAMA_BASE_URL` | Optional | `http://host.docker.internal:11434` | Reaches host Ollama from within Docker. |
| `OLLAMA_MODEL` | Optional | `qwen2.5:3b` | Local Ollama model name. |
| `ANTHROPIC_API_KEY`| Optional | `""` | Required only when `MODEL_PROVIDER=anthropic`. |
| `ANTHROPIC_MODEL` | Optional | `claude-sonnet-4-5` | Cloud Claude model identifier. |
| `DATABASE_URL` | Required | `postgresql+asyncpg://lenny:lenny@postgres:5432/lenny` | Async SQLAlchemy connection URL. |
| `SECRET_KEY` | Required | `change-me-in-local-dev...` | HMAC secret for signing client session cookies. |
| `TRANSCRIPTS_DIR` | Optional | `/data/transcripts` | Path to transcripts mounted in container. |
| `INGEST_ON_STARTUP`| Optional | `true` | Runs idempotent ingestion in background on boot. |
| `RETRIEVAL_MIN_SCORE`| Optional | `0.03` | Minimum normalized `ts_rank_cd` threshold. |
| `RETRIEVAL_FALLBACK_MIN_SCORE`| Optional | `0.12` | Stricter score threshold for fallback matches. |

---

## Model Configuration

### Option A: Local Ollama (Default & Mandatory for Demo)
1. Ensure Ollama is running on your host machine:
   ```bash
   ollama run qwen2.5:3b "Hello!"
   ```
2. The backend connects via `http://host.docker.internal:11434`.
3. The UI header badge displays: `Ollama (Local) · qwen2.5:3b` with a green indicator dot.

### Option B: Cloud Anthropic Claude
1. Open `.env` and set:
   ```env
   MODEL_PROVIDER=anthropic
   ANTHROPIC_API_KEY=sk-ant-api03-...
   ANTHROPIC_MODEL=claude-sonnet-4-5
   ```
2. Restart the backend container:
   ```bash
   docker compose restart backend
   ```
3. If `ANTHROPIC_API_KEY` is omitted while `MODEL_PROVIDER=anthropic`, the UI badge displays `Anthropic Claude · Key Missing` and `/health` returns 200 without crashing the app.

---

## Agent Skills & Claude Artifacts

### 1. Ship 30 for 30 Essay Skill
Encoded in `backend/app/agent/skills/ship30/` (`SKILL.md` + `prompts.py`).
- Follows core Ship 30 for 30 writing principles: strong headline hook, narrative progression, actionable bullet lists, bold takeaways, ~1,250 words.
- All arguments and examples cite specific transcript guests.
- Output is rendered as a clean Markdown Artifact in the side pane.

### 2. Interactive Sandboxed HTML Artifacts
When a user asks for interactive calculators, frameworks, or visual widgets:
- The assistant produces complete HTML/CSS/JS code.
- **Backend Defense**: Cleaned using Rust's `nh3` HTML sanitizer.
- **Frontend Defense**: Rendered inside an `<iframe sandbox="allow-scripts">` without `allow-same-origin`, preventing access to cookies or parent windows.

---

## Evaluation Suite (20 Questions, 100% Score)

We built an automated 20-question grounding benchmark (`backend/tests/eval/eval_set.py`):
- **15 In-Corpus Questions**: Product-market fit, activation rates, pricing, retention loops, founder mode, PLG transition, marketplace metrics, etc.
- **5 Out-of-Corpus Questions**: Aerodynamics of Boeing 777, aspirin chemical synthesis, Neapolitan pizza recipe, Napoleon at Waterloo 1815, nonsense control query.

Run the benchmark inside the backend container:
```bash
docker compose exec backend python -m tests.eval.eval_set
```

### Benchmark Results:
```
======================================================================
LENNY GROWTH ASSISTANT — 20-QUESTION GROUNDING & RETRIEVAL BENCHMARK
======================================================================
  • In-Corpus Retrieval Coverage: 15/15 (100.0%)
  • In-Corpus Topic Relevance:    15/15 (100.0%)
  • Out-of-Corpus Refusal Rate:   5/5 (100.0%)
  • Overall Benchmark Score:      20/20 (100.0%)
======================================================================
```

---

## Running Automated Tests

Run the full backend test suite (isolated in temporary test database):
```bash
docker compose exec backend pytest -v
```
**Results**: `89 passed, 0 failed in 117s`.

Run the retrieval sanity check against real indexed episodes:
```bash
docker compose exec backend python -m tests.eval.retrieval_check
```

---

## Manual UI Test Plan

A complete manual test matrix covering session isolation, streaming, inline citation chips, artifact copying, and offline degradation is documented in **[`docs/manual-ui-test-plan.md`](docs/manual-ui-test-plan.md)**.

---

## Troubleshooting

- **Ollama Host Connection Refused**:
  - Verify Ollama is running on your host machine: `curl http://localhost:11434/api/tags`.
  - In Docker Compose, the API reaches the host via `http://host.docker.internal:11434`.
  - Ensure Windows Defender / firewall allows incoming connections on port 11434.
- **Port 5173 or 8000 Already in Use**:
  - Change host ports in `docker-compose.yml` (e.g. `"3000:80"` for web, `"8001:8000"` for backend).
- **Database Reset**:
  - If you need a clean database rebuild: `docker compose down -v && docker compose up --build -d`.

---

## Technical Trade-offs

1. **PostgreSQL Full-Text Search vs. Vector Embeddings**:
   - Rather than deploying an external vector DB (Milvus, Pinecone, Chroma) with heavyweight embedding models, we used PostgreSQL 16 weighted full-text search (`setweight(header, 'A') || setweight(text, 'B')`).
   - *Result*: 5.5ms query latency, zero cold-start embedding generation overhead, exact quote and guest name precision, zero vector DB operational cost.
2. **Deterministic Sequence Ordering**:
   - Multiple messages inserted in the same transaction get identical timestamps. We added an explicit PostgreSQL `Identity(start=1)` monotonically increasing `seq` column, ensuring 100% deterministic message rendering: `order_by(Message.created_at, Message.seq)`.
3. **Artifact Security**:
   - Defense-in-depth: untrusted HTML is sanitized server-side with `nh3` before storage and isolated in a sandboxed iframe with scripts enabled but `allow-same-origin` stripped.

---

## Demo Video

- **Video Walkthrough (YouTube)**: *[Demo Video Link](https://youtu.be/placeholder)*
- **Demo Script & Guide**: See [`docs/video-script.md`](docs/video-script.md).
