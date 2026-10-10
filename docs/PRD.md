# Product Requirements: Lenny Growth Assistant

A take-home full-stack AI chat app that answers growth and product questions from Lenny’s Podcast transcripts, with citations, a writing skill, and a sandboxed artifact viewer.

## 1. Primary user and problem

**Primary user:** A product, growth, or founder operator who already trusts Lenny’s Podcast and wants advice they can trace to a specific episode—not generic LLM opinion.

**Problem:** Transcripts are long, scattered across ~300 markdown files, and hard to query. People need fast, cited answers and a way to turn those insights into a short essay or visual artifact without leaving a chat.

## 2. Success metric

**Primary (measurable in the take-home):** Of 20 fixed evaluation questions (10 in-corpus, 5 out-of-corpus, 5 essay/artifact), **≥90% of in-corpus answers include at least one episode citation (title + guest + YouTube URL)** and **100% of out-of-corpus answers explicitly say the transcripts do not support a claim.** Essay runs produce ~1,250 words with hook, headings, bullets, and a takeaway.

**Secondary:** Median cited-answer latency **< 8s** on Claude when configured; local Ollama path **completes without crashing** even if quality is lower. Docker Compose `up` brings API, web, and Postgres to a usable UI **with only host Ollama** (no Anthropic key required). First boot runs idempotent ingest and logs episode/chunk counts.

## 3. Decisions

Locked from product review (2026-10-09). Architecture and design must follow these.

| ID | Decision |
|----|----------|
| D1 | **Auth:** Anonymous sessions only. HTTP-only cookie holds a session ID; Postgres stores that session plus `user_metadata` JSON. No login, passwords, or OAuth. |
| D2 | **Provider:** Chosen only via `.env` (`MODEL_PROVIDER`). No runtime UI switch. The UI shows a **read-only badge** with active provider and model. |
| D3 | **Ollama:** Runs on the **Windows host** (already installed). The API container calls `http://host.docker.internal:11434`. **Do not** add an Ollama service to Compose. |
| D4 | **Claude:** Model id from `ANTHROPIC_MODEL` (default `claude-sonnet-4-5`). `ANTHROPIC_API_KEY` is **optional**. The app must work with **Ollama only**. If the cloud provider is selected and the key is missing, show a clear, friendly message and keep the rest of the app usable. |
| D5 | **Ingest:** Automatic, **idempotent** ingest on API startup (skip unchanged files via content hash). Also expose `POST /api/ingest`. Log how many episodes and chunks were indexed (and how many files were skipped). |

## 4. Remaining assumptions

Not contradicted by the decisions above; still the working defaults.

| ID | Assumption |
|----|------------|
| A3 | **Knowledge base = episode `transcript.md` files.** Topic `index/` files are optional query hints, not the source of truth for citations. |
| A4 | Retrieval is **Postgres full-text search** (no embeddings / vector DB). |
| A5 | Chat **streams** tokens when the provider supports it; Ollama may be slower and still stream. |
| A6 | One skill in v1: **Ship 30 for 30–style essay**. Artifact generation (Markdown or HTML/CSS) is a second agent route, not a second skill pack. |
| A7 | HTML artifacts are **untrusted**: render only in a sandboxed iframe; never `eval` or inject into the app DOM. |
| A8 | Take-home audience is a **reviewer on one machine**. No multi-tenant SSO, billing, or public internet hardening beyond the risks listed below. |
| A9 | Transcripts are for **educational use**; the app cites YouTube and does not claim ownership of Lenny’s content. |
| A10 | Incomplete frontmatter (e.g. teasers missing `title` / `publish_date`) is ingested with fallbacks (`guest` + slug) rather than skipped silently without a log. |
| A11 | Default `MODEL_PROVIDER` is **`ollama`** so a checkout without an Anthropic key still chats. Reviewers set `anthropic` in `.env` when they have a key. |

## 5. Scope

### Included

- React + Vite + TypeScript chat UI with session list, message history, citations, provider badge, and split artifact pane.
- FastAPI backend, PostgreSQL (sessions, messages, timestamps, user metadata, episodes, chunks, FTS).
- Ingest pipeline: parse YAML frontmatter + timestamped dialogue, chunk, index with `tsvector`.
- Anthropic Claude via **Claude Agent SDK** when `MODEL_PROVIDER=anthropic` and a key is present; otherwise **Ollama `qwen2.5:3b` on the host**. `ANTHROPIC_API_KEY` is optional.
- Grounded Q&A: retrieve → generate → cite episode; refuse when retrieval is empty or evidence is weak.
- Skill: ~1,250-word essay (hook, headings, bullets, takeaway) grounded in retrieved chunks.
- Artifact viewer: model emits Markdown or HTML/CSS; Markdown rendered in-app; HTML in sandboxed iframe.
- Docker Compose one-command startup (**web, API, Postgres only**), host Ollama via `host.docker.internal:11434`, `.env.example`, structured JSON logs.
- Startup ingest (idempotent) plus `POST /api/ingest`; logs of episodes/chunks indexed.
- Graceful degradation: missing Anthropic key (cloud selected), Ollama down, timeouts, empty retrieval, database down.

### Intentionally excluded (and why)

| Excluded | Why |
|----------|-----|
| Login, OAuth, multi-user auth | **D1:** anonymous cookie sessions are enough. |
| Vector embeddings / hybrid search | Brief specifies Postgres FTS; embeddings add infra, cost, and eval complexity. |
| Live YouTube / web search | Answers must stay grounded in the local archive. |
| Fine-tuning or changing the local model beyond `qwen2.5:3b` | Scope control; local path is a quality/cost contrast, not a second product. |
| Runtime provider switching in the UI | **D2:** config-only; badge is display-only. |
| Ollama as a Compose service | **D3:** Ollama is already on the Windows host. |
| Full timestamp-deep-link player | Nice-to-have; citations use episode + optional timestamp string if present in the chunk. |
| Regenerating the topic index (`build-index.sh`) | Prebuilt index may be used as hints; regenerating requires Claude CLI. |
| Production observability (Datadog, etc.) | Structured logs + health endpoints are sufficient. |
| Mobile-native apps | Responsive web only. |

## 6. User flows

### 5.1 Ask a grounded question

1. User opens the app → empty chat or last session.
2. Types a question (e.g. “How did Slack think about activation?”).
3. UI shows typing/streaming state and the **active provider**.
4. Backend retrieves chunks, agent answers with citations.
5. User expands a citation to see guest, title, date, YouTube link.

### 5.2 Transcripts do not support the answer

1. User asks something outside the corpus (sports scores, latest news, private company data).
2. Retrieval is empty or below threshold.
3. Assistant states that the **transcripts do not support an answer**, does not invent episode names, and may suggest rephrasing toward product/growth topics in the archive.

### 5.3 Ship 30 for 30 essay

1. User invokes the skill (explicit command or “write a Ship 30 essay about X”).
2. Agent retrieves supporting chunks, drafts ~1,250 words with hook, headings, bullets, takeaway.
3. Essay appears in chat as Markdown; citations listed at the end.
4. Optional: user asks to turn it into an HTML artifact → opens in the viewer.

### 5.4 Artifact viewer

1. User asks for a one-pager, checklist, or styled HTML summary.
2. Agent returns `{format: markdown|html, content}`.
3. Pane opens beside chat. Markdown is sanitized and rendered; HTML loads in iframe `sandbox` (no same-origin, no top navigation).
4. User can copy source or close the pane.

### 5.5 Failure and recovery

- Missing Anthropic key while provider is `anthropic`: **friendly banner** (not a stack trace). Sessions, history, and health still load; generation is paused until the key is set **or** `.env` is switched to `ollama`.
- Ollama-only setup (no key, `MODEL_PROVIDER=ollama`): full chat works if host Ollama is up.
- Ollama down while provider is `ollama`: banner with retry; app shell still loads history.
- DB down: app shows “cannot load sessions”; health is red.
- Timeout: message marked failed; user can retry.
- Empty retrieval: honest “not in transcripts” reply, not a crash.

## 7. Acceptance criteria

- [ ] `docker compose up` starts **web, API, and Postgres only** (no Ollama container); documented env vars in `.env.example`.
- [ ] With `MODEL_PROVIDER=ollama` and no `ANTHROPIC_API_KEY`, the reviewer can chat if host Ollama is running at port 11434.
- [ ] With `MODEL_PROVIDER=anthropic` and no key: friendly UI message; app shell and history still work.
- [ ] On API startup, ingest runs automatically, is idempotent (unchanged files skipped), and logs episode + chunk counts.
- [ ] `POST /api/ingest` re-runs the same ingest and logs the same counts.
- [ ] Ingest job loads episode transcripts into `episodes` + `chunks` with FTS.
- [ ] Every successful in-corpus answer includes **episode title, guest, and YouTube URL** when those fields exist.
- [ ] Out-of-corpus / empty retrieval replies **say the transcripts do not support the answer**.
- [ ] Essay skill produces ~1,250 words with hook, headings, bullets, and a takeaway, plus citations.
- [ ] HTML artifacts render only in a **sandboxed iframe**; Markdown artifacts do not execute scripts in the parent page.
- [ ] Header badge shows **provider and model** from config (e.g. Anthropic + `ANTHROPIC_MODEL`, or Ollama `qwen2.5:3b`). No control to change provider in the UI.
- [ ] Sessions and messages persist with timestamps and optional user metadata.
- [ ] Structured logs for request id, provider, latency, retrieval hit count, and error class.
- [ ] Documented graceful handling: missing API key, Ollama down, timeouts, empty retrieval, database down.
- [ ] UI covers loading, empty, and error states (see `design.md`).

## 8. Risks and trade-offs

| Risk | Trade-off / mitigation |
|------|------------------------|
| **Hallucination** | FTS is lexical, not semantic. Prompt: answer only from retrieved text; cite or abstain. Low retrieval score → abstain. Local 3B model will hallucinate more; UI labels provider so reviewers discount quality. |
| **Latency** | Retrieval + agent + (essay ~1,250 words) can exceed 8s. Stream tokens; cap retrieved chunks (e.g. 8–12); essay may be slower by design. |
| **Cost** | Claude for every turn and long essays. Default local provider; optional key; chunk caps; no embeddings API. |
| **Local-model quality** | `qwen2.5:3b` will miss nuance and citation discipline. Treat local mode as **offline demo / cost control**, not feature parity. Same retrieval and abstain rules still apply. |
| **Data leakage** | Transcripts and chat go to Anthropic only when that provider is selected **and** a key is present. Do not log full prompts at info level; no third-party analytics in v1. Ollama keeps generation on the host. |
| **Host Ollama / Docker networking** | Windows + `host.docker.internal:11434` can fail if Ollama is bound to localhost only or the firewall blocks Docker. Document bind address; health check distinguishes “Ollama unreachable from the container.” |
| **Unsafe HTML artifact rendering** | Model-generated HTML is XSS. Iframe `sandbox` without `allow-same-origin` / `allow-top-navigation`; `srcdoc` or blob URL; strict CSP (`default-src 'none'`, limited `style-src`); strip `<script>`, event handlers on a best-effort sanitizer **in addition to** the iframe—not instead of it. |

## 9. Phased implementation plan

**Phase 0 — Foundation:** Compose (API, web, Postgres — no Ollama service), `.env.example` (`host.docker.internal:11434`), health endpoints, structured logging, cookie sessions + `user_metadata`.

**Phase 1 — Ingest & retrieval:** Startup + `POST /api/ingest`, skip unchanged files, log episode/chunk counts, FTS.

**Phase 2 — Grounded chat:** Ollama-first path (`qwen2.5:3b`), retrieve-then-answer, citations, abstain, streaming, persist messages.

**Phase 3 — Cloud provider:** Claude Agent SDK when `MODEL_PROVIDER=anthropic`; `ANTHROPIC_MODEL` with default; friendly missing-key state; read-only provider/model badge.

**Phase 4 — Skill:** Ship 30 for 30 essay route/tool, length and structure checks, grounded citations.

**Phase 5 — Artifacts:** Generate Markdown/HTML, split pane, sandboxed iframe, copy source.

**Phase 6 — Hardening:** Timeouts, provider/DB failure UX, empty retrieval copy, eval set of 20 questions, README for reviewers.

No application code in this phase of the take-home; this document is the product contract for later implementation.
