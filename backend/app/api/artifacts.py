from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_id
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.repositories.artifacts import ArtifactRepository
from app.schemas.artifacts import ArtifactRead

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


@router.get("/{artifact_id}", response_model=ArtifactRead)
async def get_artifact(
    artifact_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    client_id: Annotated[UUID, Depends(get_client_id)],
) -> ArtifactRead:
    artifact = await ArtifactRepository(db).get_owned(artifact_id, client_id)
    if artifact is None:
        raise NotFoundError("Artifact not found.")
    return ArtifactRead.model_validate(artifact)
