from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_id
from app.db.session import get_db
from app.schemas.messages import SessionDetail
from app.schemas.sessions import SessionCreate, SessionRead, SessionUpdate
from app.services.sessions import SessionService

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
async def create_session(
    db: Annotated[AsyncSession, Depends(get_db)],
    client_id: Annotated[UUID, Depends(get_client_id)],
    payload: SessionCreate | None = None,
) -> SessionRead:
    body = payload or SessionCreate()
    session = await SessionService(db).create(
        client_id=client_id,
        title=body.title,
        user_metadata=body.user_metadata,
    )
    return SessionRead.model_validate(session)


@router.get("", response_model=list[SessionRead])
async def list_sessions(
    db: Annotated[AsyncSession, Depends(get_db)],
    client_id: Annotated[UUID, Depends(get_client_id)],
) -> list[SessionRead]:
    sessions = await SessionService(db).list_for_client(client_id)
    return [SessionRead.model_validate(item) for item in sessions]


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    client_id: Annotated[UUID, Depends(get_client_id)],
) -> SessionDetail:
    session = await SessionService(db).get_owned(session_id, client_id)
    return SessionDetail.model_validate(session)


@router.patch("/{session_id}", response_model=SessionRead)
async def rename_session(
    session_id: UUID,
    payload: SessionUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    client_id: Annotated[UUID, Depends(get_client_id)],
) -> SessionRead:
    session = await SessionService(db).rename(
        session_id=session_id,
        client_id=client_id,
        title=payload.title,
    )
    return SessionRead.model_validate(session)
