# Engineering rules (binding)

These rules apply to every task. Do not add application code until a specific phase is requested. Do not add features beyond that phase.

## Backend structure (FastAPI, Python 3.12)

All backend code lives under `backend/app/`:

| Path | Responsibility |
|------|----------------|
| `main.py` | App factory, lifespan, middleware |
| `core/` | Config via pydantic-settings, structured JSON logging, custom exceptions, error handlers |
| `api/` | Routers only: health, sessions, messages, ingest, config, artifacts. **No business logic.** |
| `schemas/` | Pydantic request/response models |
| `db/` | SQLAlchemy models, async session, Alembic migrations |
| `repositories/` | **All** database queries live here |
| `services/` | Chat, retrieval, ingestion, artifacts — business logic |
| `llm/` | Base interface, Anthropic provider, Ollama provider, factory picking by env |
| `agent/` | Router that classifies question / essay / artifact, and `skills/ship30` |
| `tests/` | Unit and integration tests mirroring the structure above |

Do not invent parallel packages or put queries in services/routers.

## Engineering rules

- Type hints everywhere. Pydantic validation on all inputs. No raw SQL strings built from user input.
- Layers only call downward: `api` → `services` → `repositories`. No shortcuts (no router→repo, no service→engine, no circular imports).
- Every error returns structured JSON `{ "error": { "code", "message", "request_id" } }`. Never send stack traces to the client.
- Every request gets a `request_id`. Logs are structured JSON with `request_id`, `session_id`, `provider`, `latency_ms`.
- Config only from environment variables. Never hardcode secrets. Keep `.env.example` complete.
- Handle without crashing: missing API key, Ollama unavailable, model timeout, empty retrieval, database down. Each returns a clear message.
- Database changes only through Alembic migrations.

## Accuracy rules (grounding)

- Answers use **only** retrieved transcript chunks. If retrieval is empty or weak, reply that the transcripts do not cover it.
- Every citation must reference a chunk that was **actually retrieved**. Validate citations after generation; drop or flag any that do not match.
- Store the sources used with each assistant message.
- Evaluation set of 20 questions in `backend/tests/eval/` (15 answerable with expected episode, 5 not answerable) plus a script that reports citation accuracy and refusal accuracy.

## Workflow rules

- Work **one phase at a time**. After each phase: run the tests, fix failures, then list what was built and how to verify it.
- Never hide errors. If something fails, show the real error and fix the root cause.
- Do not add features beyond the phase the user asked for.

## Product decisions already locked (do not reopen)

Anonymous cookie sessions + `user_metadata` JSON (no login). Provider is config-only (`.env`); UI shows a read-only provider/model badge. Ollama runs on the Windows host; API reaches it at `http://host.docker.internal:11434` — **never** run Ollama in Compose. `ANTHROPIC_API_KEY` is optional; the app must work with Ollama only. `ANTHROPIC_MODEL` from env with default `claude-sonnet-4-5`. If cloud is selected without a key, friendly message, rest of app usable. Ingest is automatic and idempotent on startup (skip unchanged files) and via `POST /api/ingest`; log episodes/chunks indexed and skipped.

See `docs/PRD.md`, `docs/architecture.md`, `docs/design.md`.
