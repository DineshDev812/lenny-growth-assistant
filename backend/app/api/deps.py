from __future__ import annotations

from uuid import UUID

from fastapi import Request

from app.services.ingestion import IngestRunner


def get_client_id(request: Request) -> UUID:
    return request.state.client_id


def get_ingest_runner(request: Request) -> "IngestRunner":
    return request.app.state.ingest_runner
