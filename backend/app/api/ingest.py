import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response

from app.api.deps import get_ingest_runner
from app.core.config import get_settings
from app.core.exceptions import IngestInProgressError, UnauthorizedError
from app.schemas.ingest import IngestStatusResponse
from app.services.ingestion import IngestRunner

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


def _check_token(provided: str | None) -> None:
    expected = get_settings().ingest_token
    if expected is None:
        return
    if provided is None or not secrets.compare_digest(provided, expected):
        raise UnauthorizedError()


@router.post("", response_model=IngestStatusResponse, status_code=202)
async def trigger_ingest(
    response: Response,
    runner: Annotated[IngestRunner, Depends(get_ingest_runner)],
    wait: Annotated[bool, Query(description="Block until the run finishes and return final counts.")] = False,
    x_ingest_token: Annotated[str | None, Header()] = None,
) -> IngestStatusResponse:
    """Re-ingest transcripts (idempotent: unchanged files are skipped)."""
    _check_token(x_ingest_token)
    started = runner.start("manual")
    if not started:
        raise IngestInProgressError()
    if wait:
        await runner.wait()
        response.status_code = 200
    return await runner.snapshot()


@router.get("/status", response_model=IngestStatusResponse)
async def ingest_status(
    runner: Annotated[IngestRunner, Depends(get_ingest_runner)],
) -> IngestStatusResponse:
    return await runner.snapshot()
