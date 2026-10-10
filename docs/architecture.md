# Architecture: Lenny Growth Assistant

## 1. System overview

```
[React + Vite SPA] --HTTP/SSE--> [FastAPI in Docker]
                                      |
                    +-----------------+------------------+
                    |                                    |
              [PostgreSQL]                    [Host machine]
               sessions,                       Ollama :11434
               messages,                       qwen2.5:3b
               episodes,                       (host.docker.internal)
               chunks + FTS]
                                      |
                         [Anthropic Claude Agent SDK]
                         only if MODEL_PROVIDER=anthropic
                         and ANTHROPIC_API_KEY is set
```

Compose services: **`web`, `api`, `db` only**. Ollama is **not** in Compose. The API container uses `OLLAMA_BASE_URL=http://host.docker.internal:11434`. Active provider is **config-only** (`MODEL_PROVIDER`); `/health` and `/api/meta` feed a read-only UI badge (provider + model). Default provider is `ollama` so the stack works without an Anthropic key.

## 2. Database schema

PostgreSQL 16+. UUIDs as primary keys. Timestamps `timestamptz`.

No `users` table. Identity is the session cookie.

### `sessions`

| Column | Type | Notes |
|--------|------|--------|
| `id` | uuid PK | HTTP-only cookie `session_id` |
| `title` | text | Derived from first user message |
| `user_metadata` | jsonb | Anonymous extras: `{display_name?, user_agent?}` — not credentials |
| `created_at` / `updated_at` | timestamptz | |

### `messages`

| Column | Type | Notes |
|--------|------|--------|
| `id` | uuid PK | UUIDv4 |
| `session_id` | uuid FK | on delete cascade |
| `seq` | bigint identity | Monotonically increasing sequence `Identity(start=1)` |
| `role` | text | `user` \| `assistant` |
| `content` | text | Full assistant/user text |
| `sources` | jsonb | `[{id, chunk_id, episode_id, slug, title, guest, youtube_url, youtube_deep_link, start_ts, start_seconds, snippet}]` |
| `provider` | text null | `ollama` \| `anthropic` |
| `model` | text null | `qwen2.5:3b` \| `claude-sonnet-4-5` |
| `intent` | text null | `qa` \| `essay` \| `artifact` |
| `error_class` | text null | `provider_unconfigured`, `timeout`, … |
| `created_at` | timestamptz | Server timestamp `func.now()` |

*Deterministic read order*: `ORDER BY created_at ASC, seq ASC`.

### `artifacts`

| Column | Type | Notes |
|--------|------|--------|
| `id` | uuid PK | UUIDv4 |
| `session_id` | uuid FK | on delete cascade |
| `message_id` | uuid FK | on delete cascade, unique |
| `client_id` | uuid | Ownership check |
| `format` | text | `markdown` \| `html` |
| `title` | text | Extracted or default title |
| `content` | text | Sanitized HTML or Markdown content |
| `created_at` | timestamptz | Server timestamp `func.now()` |

### `episodes`

| Column | Type | Notes |
|--------|------|--------|
| `id` | uuid PK | UUIDv4 |
| `slug` | text unique | Folder name, e.g. `lauryn-isford` |
| `guest` | text | From frontmatter (fallback: slug) |
| `title` | text | From frontmatter (fallback: guest) |
| `youtube_url` | text null | Video URL |
| `video_id` | text null | YouTube video ID |
| `publish_date` | date null | Published date |
| `description` | text null | Episode description |
| `source_path` | text | Path for re-ingest |
| `content_hash` | text | SHA256 of source file |
| `keywords` | jsonb | Frontmatter keywords list |
| `ingested_at` | timestamptz | Server timestamp |

### `chunks`

| Column | Type | Notes |
|--------|------|--------|
| `id` | uuid PK | UUIDv4 |
| `episode_id` | uuid FK | on delete cascade |
| `chunk_index` | int | Sequence order in episode |
| `speaker` | text null | Turn speaker |
| `start_seconds` | int null | Start time in seconds |
| `text` | text | Chunk text body |
| `header` | text | Concatenated `title + guest + keywords` for search |
| `tsv` | tsvector | `GENERATED ALWAYS AS (setweight(to_tsvector('english', header), 'A') \|\| setweight(to_tsvector('english', text), 'B')) STORED` |

Indexes: GIN on `chunks.tsv`; btree on `(session_id, created_at, seq)`, `episodes.slug`, `chunks.episode_id`.

## 3. API endpoints

JSON unless noted. All mutating chat routes require the session cookie (create session on first visit).

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | `{status, db, provider, model, provider_ok, anthropic_key_present, ollama_ok}`. App process stays up if the LLM is down. Missing Anthropic key with `provider=anthropic` → `provider_unconfigured` (degraded, not a 500). |
| `GET` | `/api/meta` | `{provider, model, app_name}` for the read-only badge. |
| `POST` | `/api/sessions` | Create session. |
| `GET` | `/api/sessions` | List sessions (newest first). |
| `GET` | `/api/sessions/{id}` | Session + messages + latest artifact. |
| `PATCH` | `/api/sessions/{id}` | Title or `user_metadata`. |
| `POST` | `/api/sessions/{id}/messages` | Send user message. Body: `{content, intent?}`. Response: **SSE** (`token`, `citation`, `artifact`, `done`, `error`). |
| `GET` | `/api/artifacts/{id}` | Fetch artifact payload for the viewer. |
| `POST` | `/api/ingest` | Manual re-ingest (same idempotent job as startup). Response + logs: `{episodes_indexed, episodes_skipped, chunks_indexed}`. Protect with `INGEST_TOKEN` or compose-only network. |
| `GET` | `/api/debug/retrieval` | Optional, non-prod: query + hits for eval. |

Error shape: `{error_class, message, retryable}` with HTTP 503 (db/provider), 504 (timeout), 422 (validation), 200+SSE error event for mid-stream failure.

## 4. Component boundaries

### Frontend (`web/`)

- **Shell:** header (provider badge, health), session sidebar, main chat, artifact pane.
- **Chat:** composer, message list, citation chips, retry.
- **ArtifactViewer:** Markdown path (sanitized) vs HTML path (iframe only).
- **API client:** fetch + EventSource/fetch-stream; maps `error_class` to banners.
- No secrets; no direct DB; does not render HTML into React `dangerouslySetInnerHTML`.

### Backend (`api/`)

- **http:** routers, cookie session, timeouts, logging middleware (`request_id`).
- **db:** SQLAlchemy/asyncpg (implementation choice later), migrations.
- **ingest:** frontmatter parse, chunker, FTS upsert; runs on API startup and via `POST /api/ingest`.
- **retrieve:** query rewrite (light), `ts_rank` + limit, pack for prompt.
- **agent:** provider factory, tools (`search_transcripts`, `emit_artifact`), skill prompt for essays.
- **safety:** HTML sanitizer (defense in depth), citation normalizer.

### Agent vs HTTP

The Agent SDK owns tool loops and model I/O. FastAPI owns persistence, retrieval SQL, and SSE. The agent **calls retrieval as a tool** implemented in-process (not a public HTTP round-trip per chunk) so citations stay consistent with what was stored on the message.

## 5. Ingestion and retrieval flow

Triggered **on API startup** (after migrations) and on **`POST /api/ingest`**. Same function both times.

```
episodes/{slug}/transcript.md
        → parse YAML + body
        → skip if content_hash unchanged   # count as episodes_skipped
        → upsert episodes                  # count as episodes_indexed
        → split body on speaker/timestamp blocks, pack ~400–800 tokens, overlap ~80
        → set search_vector
           setweight(title/guest/keywords, 'A') || setweight(body, 'B')
        → COMMIT
        → log JSON: episodes_indexed, episodes_skipped, chunks_indexed
```

**Query time:**

1. User message → optional English query expansion (same provider, cheap) **or** raw query if local/slow.
2. `plainto_tsquery('english', …)` with a simple OR fallback on quoted guest names.
3. Top-k chunks (k ≈ 10) with `ts_rank_cd`, diversity: max N chunks per episode.
4. If max rank < threshold or k = 0 → **empty retrieval** path (no generation from parametric knowledge).
5. Prompt: quotes + metadata; instruction to cite `title`, `guest`, `youtube_url` and to say when unsupported.

Topic `index/*.md` is **not** ingested as chunks in v1 (avoid citing an index file as an episode). Optional later: use topic files only to boost episode slugs.

## 6. Agent routing

Single agent, tools + a router hint from the HTTP layer (`intent` inferred or explicit):

| Intent | How detected | Behavior |
|--------|----------------|----------|
| `qa` | Default | `search_transcripts` → answer + citations. |
| `essay` | Phrases like “ship 30”, “write an essay”, skill button | Retrieve more chunks; essay system prompt (~1,250 words, hook, headings, bullets, takeaway); citations appendix. |
| `artifact` | “make a one-pager / HTML / visual” | Retrieve; `emit_artifact(format, content)`; short chat ack + open pane. |
| `abstain` | Tool returned no hits | Fixed template: transcripts do not support an answer. |

Do not run essay and HTML generation in one unbounded loop without a turn cap (e.g. max 8 tool calls).

## 7. Model toggle

Config only (restart the API container to change). UI never writes these values.

```
MODEL_PROVIDER=ollama|anthropic          # default: ollama
ANTHROPIC_API_KEY=                       # optional
ANTHROPIC_MODEL=claude-sonnet-4-5        # default if unset
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:3b
```

`get_provider()` returns a common interface: `stream_chat(messages, tools)`.

- **`ollama`:** HTTP to host Ollama. Works with an empty Anthropic key. Adapter shares the same tool JSON as the cloud path.
- **`anthropic`:** Claude Agent SDK. Model string = `ANTHROPIC_MODEL` (default `claude-sonnet-4-5`). If the key is missing, **do not crash**; return `provider_unconfigured` and a friendly message payload for the UI.

Health: `anthropic` + no key → `provider_unconfigured` (app up, generation blocked). `ollama` + connection fail → `provider_down`. Extra: probe host Ollama even when provider is Anthropic if useful for the badge, but do not fail `/health` as hard-down.

## 8. Security

- Secrets only in env; never shipped to the client.
- Session cookie: `HttpOnly`, `SameSite=Lax`, `Secure` when HTTPS.
- `INGEST_TOKEN` for ingest endpoint; not exposed on the SPA.
- Prompt/log redaction: do not log full transcript chunks at info; debug opt-in.
- Artifacts: store raw HTML but serve to the iframe with `Content-Security-Policy: sandbox` equivalent via iframe flags: `sandbox=""` or `allow-scripts` **off**. Prefer **no scripts**. If styling needs inline CSS, allow `style` attributes / `<style>` inside iframe only.
- Prompt injection: retrieved text is untrusted; wrap in delimiters; tools cannot fetch arbitrary URLs.
- CORS: web origin only.

## 9. Deployment topology (local take-home)

```
Host (Windows)
  Ollama listening on 11434          # not started by Compose
  Docker Desktop
    docker-compose.yml
      db:   postgres:16, volume pgdata, healthcheck
      api:  FastAPI
            extra_hosts: host.docker.internal:host-gateway  # if needed
            waits on db → migrations → ingest (idempotent) → serve
            OLLAMA_BASE_URL=http://host.docker.internal:11434
      web:  Vite preview or nginx-static, proxies /api and /health
```

- `.env.example` documents every variable, including optional `ANTHROPIC_API_KEY` and default `MODEL_PROVIDER=ollama`.
- Structured logs: JSON lines on stdout (`timestamp`, `level`, `request_id`, `event`, `latency_ms`, `provider`, `retrieval_hits`, `error_class`). Ingest logs include `episodes_indexed`, `episodes_skipped`, `chunks_indexed`.
- Graceful failure: API **stays up** if the LLM is down or the Anthropic key is absent; `/health` reports dependency status; UI reads it on load and on error.

Reviewer path: ensure host Ollama is running (`qwen2.5:3b` pulled), copy `.env.example` → `.env`, `docker compose up --build`.
