# Engineering Decisions & Audit Log

This document records architectural decisions, identified pitfalls, failed attempts, and resolutions for the Lenny Growth Assistant project. It serves as persistent context and feeds into the take-home audit requirements.

---

## 1. Phase 3 Audit & First Fixes (2026-10-10)

### 1.1 Message Sequence Ordering (`messages.seq`)
- **Problem**: When user and placeholder assistant messages are inserted in the same transaction or same second, PostgreSQL assigns identical `created_at` timestamps. Reading messages ordered solely by `created_at` resulted in non-deterministic message order in chat history.
- **Decision**: Add a monotonically increasing `seq` column (`sa.BigInteger`, `sa.Identity(start=1)`) to the `messages` table via migration `0003_message_seq`. Add compound index on `["session_id", "created_at", "seq"]`.
- **Implementation**:
  - Migration `backend/app/db/migrations/versions/0003_add_message_seq.py`.
  - SQLAlchemy model `Message.seq: Mapped[int] = mapped_column(BigInteger, Identity(start=1), nullable=False)`.
  - `Session.messages` relationship configured with `order_by=(Message.created_at, Message.seq)`.
  - Added test `test_messages_ordered_by_monotonic_seq` in `test_sessions.py`.

### 1.2 Ingest Concurrency Conflict (`409 ingest_in_progress`)
- **Problem**: Calling `POST /api/ingest` while an ingestion was already actively executing returned status 202 instead of signalling a conflict, violating the contract.
- **Decision**: Define `IngestInProgressError(AppError)` with HTTP 409 and code `ingest_in_progress`.
- **Implementation**:
  - Added `IngestInProgressError` in `backend/app/core/exceptions.py`.
  - In `backend/app/api/ingest.py`, check `started = runner.start("manual")`. If `False`, immediately raise `IngestInProgressError`.
  - Added test `test_post_ingest_conflict_when_already_running` in `test_ingest_search_api.py`.

### 1.3 Weighted Retrieval Vector (`guest / title / keywords` + body)
- **Problem**: The initial Phase 3 implementation computed `chunks.tsv` solely from `chunks.text`. If a user asked a query containing a guest's name (e.g. "Elena Verna pricing") or episode topic (e.g. "Lovable ARR"), strict full-text search (`websearch_to_tsquery`) failed because the speaker line only contained "Elena" or the guest name was only in frontmatter metadata. This triggered noisy OR-fallback where unrelated episodes scored higher than the actual interview.
- **Decision**:
  - Store frontmatter `keywords` on `episodes` table as JSONB.
  - Store a `header` text column on `chunks` (`f"{title} {guest} {' '.join(keywords)}"`).
  - Compute `chunks.tsv` as:
    `setweight(to_tsvector('english'::regconfig, header), 'A') || setweight(to_tsvector('english'::regconfig, text), 'B')`
    persisted and indexed with a GIN index.
  - Header terms receive Weight 'A' (4x boost in `ts_rank_cd`), while body dialogue text receives Weight 'B'.
  - Bump hash salt in `hash_content` from `v1:` to `v2:` to trigger automatic re-indexing across all 303 episodes.
- **Implementation**:
  - Migration `backend/app/db/migrations/versions/0004_keywords_and_weighted_search.py`.
  - Updated `EpisodeRepository.replace_episode` to store keywords and chunk headers.
  - Updated `backend/app/services/ingestion.py` with `v2:` salt and chunk header builder.
  - Added tests in `test_ingest_search_api.py` and `test_retrieval.py` verifying searches by guest name ("Ada Activation") and keyword ("aha moment") rank expected episodes first.
  - Query latency remains blazing fast (~5.5 ms on 15,147 chunks).

### 1.4 Docker Test Fixtures & Container Image Rebuild
- **Failed Attempt**: Running pytest initially failed on `assert status.episodes_ingested == 5` with `AssertionError: assert 8 == 5`.
- **Root Cause**: The running Docker container had 3 stale fixture folders (`casey-market`, `ada-loop`, `plain-notes`) preserved from an earlier pre-merge state before commit `d506eb5`.
- **Resolution**: Removed the 3 stale directories from the container. All 90 unit and integration tests passed cleanly. Rebuilt the Docker image using `docker compose build backend` to guarantee clean reproducibility.

### 1.5 Real Data Retrieval Sanity Check
- Ran `docker compose exec backend python -m tests.eval.retrieval_check`.
- Results: 10/10 growth questions returned top-ranked episode chunks with high relevance scores, speaker names, timestamps, and deep links. Control nonsense query returned 0 results.
