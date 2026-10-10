from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Artifact


class ArtifactRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        *,
        session_id: UUID,
        message_id: UUID,
        client_id: UUID,
        format: str,
        title: str,
        content: str,
    ) -> Artifact:
        artifact = Artifact(
            session_id=session_id,
            message_id=message_id,
            client_id=client_id,
            format=format,
            title=title,
            content=content,
        )
        self._db.add(artifact)
        await self._db.flush()
        await self._db.refresh(artifact)
        return artifact

    async def get_owned(self, artifact_id: UUID, client_id: UUID) -> Artifact | None:
        result = await self._db.execute(
            select(Artifact).where(Artifact.id == artifact_id, Artifact.client_id == client_id)
        )
        return result.scalar_one_or_none()
