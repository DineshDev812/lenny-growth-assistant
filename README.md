# lenny-growth-assistant

Chat assistant over Lenny's Podcast transcripts. See `docs/` for the PRD, architecture and design.

## Phase 3: transcript ingestion and retrieval

Put the transcripts at `data/transcripts/episodes/{guest-slug}/transcript.md` (the folder is git-ignored and is
mounted read-only into the backend container at `/data/transcripts`).

```bash
docker compose up --build            # migrations run, then ingestion starts in the background
curl localhost:8000/api/ingest/status # state + counts (episodes ingested/skipped/failed, chunks created)
curl -X POST "localhost:8000/api/ingest?wait=true"   # re-ingest; unchanged files are skipped
```

- `GET /api/search?q=...&k=6` returns the top transcript chunks (Postgres full-text search) with a YouTube
  deep link and start timestamp. Empty or nonsense queries return an empty list.
- If `INGEST_TOKEN` is set, `POST /api/ingest` needs the header `X-Ingest-Token`.
- Tests (use a separate `<db>_test` database, never the real data):
  `docker compose exec backend pytest`
- Retrieval sanity check against the real data:
  `docker compose exec backend python -m tests.eval.retrieval_check`
