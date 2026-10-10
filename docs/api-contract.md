# Lenny Growth Assistant — Binding API Contract

This document defines the binding HTTP and SSE contract for the Lenny Growth Assistant. All endpoints, payloads, headers, and error behaviors documented here are final and strictly enforced across backend services, agent layer, and frontend client.

---

## 1. Global Conventions

### 1.1 Headers
- **`X-Request-ID`**: Every incoming request may provide an `X-Request-ID` header. If absent, the backend generates a UUIDv4. All responses (including error responses and SSE initial headers) must echo `X-Request-ID`.
- **`Cookie`**: Session identification uses a signed HTTP-only anonymous client cookie (`client_id`). If absent, one is issued on the response (`Set-Cookie`). All mutating session operations require and enforce client ownership.
- **`Accept`**:
  - `application/json` (default) for standard JSON responses.
  - `text/event-stream` for Server-Sent Events (SSE) streaming on message creation.

### 1.2 Structured Error Format
All errors return HTTP status with the standard JSON shape:
```json
{
  "error": {
    "code": "string",
    "message": "string",
    "request_id": "string"
  }
}
```
Stack traces are never returned to clients.

#### Standard Error Codes & Status Codes:
| Error Code | HTTP Status | Description |
|---|---|---|
| `validation_error` | 422 | Request body, query param, or path param validation failed. |
| `not_found` | 404 | Resource does not exist or is not owned by the requesting client. |
| `forbidden` | 403 | Client is authenticated but lacks required permission. |
| `unauthorized` | 401 | Missing or invalid authentication/admin token (e.g. `X-Ingest-Token`). |
| `ingest_in_progress` | 409 | A manual re-ingest was requested while an ingestion job is actively running. |
| `db_down` | 503 | PostgreSQL database connection unreachable or timed out. |
| `provider_unconfigured` | 503 | Selected provider (e.g. Anthropic) lacks required API keys or config. |
| `provider_unavailable` | 503 | Configured LLM host (e.g. local Ollama) is unreachable or returned connection refused. |
| `provider_timeout` | 504 | LLM provider took longer than the configured timeout limit. |
| `internal_error` | 500 | Unexpected internal server exception. |

---

## 2. Core Schemas

### 2.1 Source Object
Represents a grounded transcript chunk citation returned with an answer:
```json
{
  "id": "S1",
  "chunk_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "episode_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "slug": "lauryn-isford",
  "title": "Mastering onboarding | Lauryn Isford (Head of Growth at Airtable)",
  "guest": "Lauryn Isford",
  "publish_date": "2023-04-12",
  "youtube_url": "https://www.youtube.com/watch?v=dLku0AiGPVA",
  "youtube_deep_link": "https://www.youtube.com/watch?v=dLku0AiGPVA&t=1598",
  "start_ts": "00:26:38",
  "start_seconds": 1598,
  "snippet": "Of course, the metric should be correlated with retention no matter what..."
}
```

### 2.2 Artifact Summary Object
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "format": "markdown",
  "title": "The Onboarding Engine: A Ship 30 Guide"
}
```
*`format` must be either `"markdown"` or `"html"`.*

### 2.3 Message Object
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "role": "assistant",
  "content": "To improve activation, identify the specific action...",
  "sources": [ ... ],
  "provider": "ollama",
  "model": "qwen2.5:3b",
  "intent": "qa",
  "error_class": null,
  "artifact": null,
  "created_at": "2026-10-10T12:00:00Z"
}
```
*Note: Reads must always order deterministically by `(created_at, seq)`.*

---

## 3. Endpoints

### 3.1 Health & Meta

#### `GET /health`
Returns system status. A down LLM provider **never** causes `/health` to return 5xx; only a down database returns 503 `db_down`.
- **Response 200 OK**:
```json
{
  "status": "ok",
  "db": "ok",
  "provider": "ollama",
  "model": "qwen2.5:3b",
  "provider_status": "ok"
}
```
- Possible values for `provider_status`: `"ok" | "unconfigured" | "unavailable" | "unknown"`.

#### `GET /api/meta`
Public metadata for the client UI header badge.
- **Response 200 OK**:
```json
{
  "app_name": "Lenny Growth Assistant",
  "provider": "ollama",
  "model": "qwen2.5:3b",
  "fallback_provider": null,
  "provider_status": "ok"
}
```

---

### 3.2 Sessions

#### `POST /api/sessions`
Create a new chat session.
- **Request Body (optional)**:
```json
{
  "title": "New chat",
  "user_metadata": {}
}
```
- **Response 201 Created**:
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "New chat",
  "user_metadata": {},
  "created_at": "2026-10-10T12:00:00Z",
  "updated_at": "2026-10-10T12:00:00Z"
}
```

#### `GET /api/sessions`
List all sessions owned by the client cookie, ordered by `updated_at DESC`.
- **Response 200 OK**:
```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "title": "Onboarding activation benchmarks",
    "user_metadata": {},
    "created_at": "2026-10-10T12:00:00Z",
    "updated_at": "2026-10-10T12:05:00Z"
  }
]
```

#### `GET /api/sessions/{id}`
Retrieve a session with all its messages and latest artifact summary.
- **Response 200 OK**:
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "Onboarding activation benchmarks",
  "user_metadata": {},
  "created_at": "2026-10-10T12:00:00Z",
  "updated_at": "2026-10-10T12:05:00Z",
  "messages": [ ...Message Objects... ]
}
```
- **Error 404 Not Found**: If session does not exist or belongs to another client.

#### `PATCH /api/sessions/{id}`
Rename a session.
- **Request Body**:
```json
{
  "title": "Activation frameworks summary"
}
```
- **Response 200 OK**: Updated `SessionDetail` or `SessionRead`.
- **Error 404 Not Found**: If not owned by client.

---

### 3.3 Messages & SSE Streaming

#### `POST /api/sessions/{id}/messages`
Send a user message. Supports both regular JSON and Server-Sent Events (SSE).

- **Request Body**:
```json
{
  "content": "How do you improve activation for new users?",
  "intent": null,
  "artifact_format": null
}
```
  - `content`: `string`, 1 to 20,000 characters.
  - `intent`: `"qa" | "essay" | "artifact" | null` (optional classification hint).
  - `artifact_format`: `"markdown" | "html" | null`.

#### Path A: Standard JSON (`Accept: application/json`)
- **Response 201 Created**:
```json
{
  "user_message": { ...Message Object... },
  "assistant_message": { ...Message Object... },
  "artifact": { ...ArtifactRead or null... }
}
```

#### Path B: Server-Sent Events (`Accept: text/event-stream`)
- **Response 200 OK** (`Content-Type: text/event-stream; charset=utf-8`):
Stream event protocol follows the format:
```
event: <name>
data: <json>

```

#### SSE Event Sequence:
1. **`event: start`** (Immediate acknowledgement):
   ```json
   {
     "user_message_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
     "intent": "qa",
     "provider": "ollama",
     "model": "qwen2.5:3b"
   }
   ```
2. **`event: sources`** (Sent immediately after retrieval, before any generation token):
   ```json
   {
     "sources": [ ...Source Objects... ]
   }
   ```
3. **`event: token`** (Repeated per chunk of generated text):
   ```json
   {
     "text": "Activation "
   }
   ```
4. **`event: artifact`** (Optional, emitted when an essay/artifact is produced):
   ```json
   {
     "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
     "format": "markdown",
     "title": "The Onboarding Engine: A Ship 30 Guide"
   }
   ```
5. **`event: error`** (Sent if a failure occurs mid-stream):
   ```json
   {
     "error": {
       "code": "provider_timeout",
       "message": "Model generation timed out.",
       "request_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
     },
     "retryable": true
   }
   ```
   *Note: Even upon mid-stream failure, a friendly fallback assistant message with `error_class` is persisted in the session history so the conversation remains intact.*
6. **`event: done`** (Stream completion terminal event):
   ```json
   {
     "assistant_message": { ...Message Object... },
     "artifact": null
   }
   ```

---

### 3.4 Artifacts

#### `GET /api/artifacts/{id}`
Fetch the full payload of a generated artifact for display in the side pane.
- **Security**: Only the owning anonymous client may retrieve it. Other clients receive 404.
- **Sanitization**: Any HTML content returned is pre-sanitized on the backend. The frontend iframe renders it inside an isolated sandbox (`sandbox="allow-scripts"` without `allow-same-origin`).
- **Response 200 OK**:
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "message_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "format": "markdown",
  "title": "The Onboarding Engine",
  "content": "# The Onboarding Engine\n\n...",
  "created_at": "2026-10-10T12:00:00Z"
}
```
- **Error 404 Not Found**: Resource not found or client not authorized.

---

### 3.5 Ingest & Search (Operations & Debug)

#### `POST /api/ingest`
Trigger transcript ingestion. Idempotent: skips unchanged content hashes.
- **Query Parameters**:
  - `wait`: `boolean` (default `false`). If `true`, blocks until complete and returns 200; if `false`, returns 202 immediately.
- **Headers**:
  - `X-Ingest-Token`: required if `INGEST_TOKEN` is set in config. Returns 401 if invalid.
- **Response 202 Accepted** (when `wait=false`):
```json
{
  "state": "running",
  "trigger": "manual",
  "started_at": "2026-10-10T12:00:00Z"
}
```
- **Response 200 OK** (when `wait=true`):
```json
{
  "state": "completed",
  "episodes_ingested": 0,
  "episodes_skipped": 303,
  "episodes_failed": 0,
  "episodes_deleted": 0,
  "chunks_created": 0,
  "total_episodes": 303,
  "total_chunks": 15147
}
```
- **Error 409 Conflict (`ingest_in_progress`)**: If an ingestion run is already active.

#### `GET /api/ingest/status`
Returns current ingestion status, counts, and any recorded file errors. Never returns 5xx even if the database is temporarily unreachable.

#### `GET /api/search`
Debug search endpoint over Postgres full-text search.
- **Query Parameters**:
  - `q`: search query string (required, 1..500 chars).
  - `k`: number of top results (default `6`, min `1`, max `50`).
- **Response 200 OK**:
```json
{
  "query": "activation",
  "k": 6,
  "count": 6,
  "results": [
    {
      "chunk_id": "...",
      "episode_id": "...",
      "episode_slug": "activation-expert",
      "episode_title": "Ada Activation: Getting new users to their aha moment",
      "guest": "Ada Activation",
      "publish_date": "2023-03-14",
      "youtube_url": "https://www.youtube.com/watch?v=ACT1VATE001",
      "youtube_deep_link": "https://www.youtube.com/watch?v=ACT1VATE001&t=21",
      "chunk_index": 0,
      "speaker": "Ada Activation",
      "start_seconds": 21,
      "start_timestamp": "00:00:21",
      "text": "...",
      "score": 0.82
    }
  ]
}
```
