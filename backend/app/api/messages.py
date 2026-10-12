from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import Response, StreamingResponse

from app.api.deps import get_client_id
from app.core.config import get_settings
from app.core.exceptions import MessageTooLongError
from app.db.session import SessionLocal
from app.schemas.messages import MessageCreate, SendMessageResponse
from app.services.chat import ChatService

router = APIRouter(prefix="/api/sessions", tags=["messages"])


def _extract_request_id(request: Request, x_request_id: str | None) -> str:
    rid = getattr(request.state, "request_id", None) or x_request_id
    return str(rid) if rid else str(uuid4())


@router.post(
    "/{session_id}/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    session_id: UUID,
    payload: MessageCreate,
    request: Request,
    client_id: Annotated[UUID, Depends(get_client_id)],
    accept: Annotated[str | None, Header()] = None,
    x_request_id: Annotated[str | None, Header()] = None,
) -> Response:
    req_id = _extract_request_id(request, x_request_id)
    settings = get_settings()

    if len(payload.content) > settings.max_message_chars:
        raise MessageTooLongError(
            f"Message exceeds maximum allowed length of {settings.max_message_chars} characters."
        )

    chat_service = ChatService(session_factory=SessionLocal)

    is_sse = accept and "text/event-stream" in accept

    if is_sse:
        return StreamingResponse(
            chat_service.stream_message(
                session_id=session_id,
                client_id=client_id,
                content=payload.content,
                request_id=req_id,
                explicit_intent=payload.intent,
                artifact_format=payload.artifact_format,
            ),
            media_type="text/event-stream",
            headers={
                "X-Request-ID": req_id,
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    res = await chat_service.send_message_sync(
        session_id=session_id,
        client_id=client_id,
        content=payload.content,
        explicit_intent=payload.intent,
        artifact_format=payload.artifact_format,
    )
    return Response(
        content=res.model_dump_json(),
        media_type="application/json",
        status_code=status.HTTP_201_CREATED,
        headers={"X-Request-ID": req_id},
    )
