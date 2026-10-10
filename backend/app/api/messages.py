from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_id
from app.db.session import get_db
from app.schemas.messages import MessageCreate, MessageRead, SendMessageResponse
from app.services.messages import MessageService

router = APIRouter(prefix="/api/sessions", tags=["messages"])


@router.post(
    "/{session_id}/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    session_id: UUID,
    payload: MessageCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    client_id: Annotated[UUID, Depends(get_client_id)],
) -> SendMessageResponse:
    user_message, assistant_message = await MessageService(db).add_user_message(
        session_id=session_id,
        client_id=client_id,
        content=payload.content,
    )
    return SendMessageResponse(
        user_message=MessageRead.model_validate(user_message),
        assistant_message=MessageRead.model_validate(assistant_message),
    )
