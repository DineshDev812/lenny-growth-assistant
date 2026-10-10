from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.prompts import format_qa_prompt
from app.agent.router import classify_intent
from app.agent.skills.ship30.prompts import format_ship30_prompt
from app.core.config import get_settings
from app.core.exceptions import AppError, NotFoundError, ProviderUnavailableError
from app.db.models import Artifact, Message, Session
from app.llm.base import LLMMessage
from app.llm.factory import get_llm_provider
from app.repositories.artifacts import ArtifactRepository
from app.repositories.messages import MessageRepository
from app.repositories.sessions import SessionRepository
from app.schemas.artifacts import ArtifactRead, ArtifactSummary
from app.schemas.messages import MessageRead, SendMessageResponse, Source
from app.schemas.retrieval import RetrievedChunk
from app.services.retrieval import RetrievalService
from app.services.sanitizer import sanitize_html

logger = logging.getLogger(__name__)

EMPTY_RETRIEVAL_MESSAGE = (
    "The transcripts I have don't support an answer to this. "
    "Try asking about a product, growth, or career topic covered on Lenny's Podcast."
)

_TITLE_MAX = 60


def _build_sources(chunks: list[RetrievedChunk]) -> tuple[list[Source], str]:
    sources: list[Source] = []
    lines: list[str] = []
    for idx, c in enumerate(chunks, start=1):
        sid = f"S{idx}"
        snippet = " ".join(c.text.split())[:300]
        s = Source(
            id=sid,
            chunk_id=c.chunk_id,
            episode_id=c.episode_id,
            slug=c.episode_slug,
            title=c.episode_title,
            guest=c.guest,
            publish_date=str(c.publish_date) if c.publish_date else None,
            youtube_url=c.youtube_url,
            youtube_deep_link=c.youtube_deep_link or c.youtube_url,
            start_ts=c.start_timestamp,
            start_seconds=c.start_seconds,
            snippet=snippet,
        )
        sources.append(s)
        lines.append(
            f"[{sid}] Episode: {c.episode_title} | Guest: {c.guest} | Time: {c.start_timestamp or 'N/A'}\n"
            f"Transcript Quote: {c.text}\n"
        )
    return sources, "\n".join(lines)


def _extract_title(text: str, fallback: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        first = lines[0].lstrip("#").strip()
        if len(first) > 5 and len(first) <= 80:
            return first
    return fallback


class ChatService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._sessions = SessionRepository(db)
        self._messages = MessageRepository(db)
        self._artifacts = ArtifactRepository(db)
        self._retrieval = RetrievalService(db)

    async def _get_session(self, session_id: UUID, client_id: UUID) -> Session:
        session = await self._sessions.get_owned(session_id, client_id)
        if session is None:
            raise NotFoundError("Session not found.")
        return session

    async def send_message_sync(
        self,
        *,
        session_id: UUID,
        client_id: UUID,
        content: str,
        explicit_intent: str | None = None,
        artifact_format: str | None = None,
    ) -> SendMessageResponse:
        session = await self._get_session(session_id, client_id)
        is_first = len(session.messages) == 0

        intent = classify_intent(content, explicit_intent)
        user_msg = await self._messages.create(
            session_id=session.id,
            role="user",
            content=content,
            sources=[],
        )
        user_msg.intent = intent

        # Retrieval
        chunks = await self._retrieval.retrieve(content, k=4 if intent == "qa" else 6)
        sources, sources_context = _build_sources(chunks)

        settings = get_settings()
        provider = get_llm_provider(settings)

        artifact_obj: Artifact | None = None
        assistant_content = ""

        if not chunks:
            assistant_content = EMPTY_RETRIEVAL_MESSAGE
            sources = []
        else:
            if intent == "essay":
                system_prompt = format_ship30_prompt(sources_context)
            else:
                system_prompt = format_qa_prompt(sources_context)

            llm_res = await provider.generate(
                messages=[LLMMessage(role="user", content=content)],
                system_prompt=system_prompt,
            )
            assistant_content = llm_res.content

        assistant_msg = await self._messages.create(
            session_id=session.id,
            role="assistant",
            content=assistant_content,
            sources=[s.model_dump(mode="json") for s in sources],
            provider=provider.provider_name,
            model=provider.model_name,
            intent=intent,
            error_class=None,
        )

        if intent in ("essay", "artifact") and assistant_content:
            art_fmt = artifact_format or ("markdown" if intent == "essay" else "html")
            art_title = _extract_title(assistant_content, f"Lenny Growth {intent.capitalize()}")
            art_body = assistant_content
            if art_fmt == "html":
                art_body = sanitize_html(art_body)

            artifact_obj = await self._artifacts.create(
                session_id=session.id,
                message_id=assistant_msg.id,
                client_id=client_id,
                format=art_fmt,
                title=art_title,
                content=art_body,
            )
            assistant_msg.artifact = artifact_obj

        # Touch session and set title on first turn
        new_title = content[:_TITLE_MAX] if is_first and session.title == "New chat" else None
        await self._sessions.touch(session, title=new_title)

        return SendMessageResponse(
            user_message=MessageRead.model_validate(user_msg),
            assistant_message=MessageRead.model_validate(assistant_msg),
            artifact=ArtifactRead.model_validate(artifact_obj) if artifact_obj else None,
        )

    async def stream_message(
        self,
        *,
        session_id: UUID,
        client_id: UUID,
        content: str,
        request_id: str,
        explicit_intent: str | None = None,
        artifact_format: str | None = None,
    ) -> AsyncIterator[str]:
        session = await self._get_session(session_id, client_id)
        is_first = len(session.messages) == 0

        intent = classify_intent(content, explicit_intent)
        user_msg = await self._messages.create(
            session_id=session.id,
            role="user",
            content=content,
            sources=[],
        )
        user_msg.intent = intent

        settings = get_settings()
        provider = get_llm_provider(settings)

        # 1. Event: start
        start_payload = {
            "user_message_id": str(user_msg.id),
            "intent": intent,
            "provider": provider.provider_name,
            "model": provider.model_name,
        }
        yield f"event: start\ndata: {json.dumps(start_payload)}\n\n"

        # 2. Retrieval & Event: sources
        chunks = await self._retrieval.retrieve(content, k=4 if intent == "qa" else 6)
        sources, sources_context = _build_sources(chunks)
        yield f"event: sources\ndata: {json.dumps({'sources': [s.model_dump(mode='json') for s in sources]})}\n\n"

        assistant_tokens: list[str] = []
        error_class: str | None = None
        artifact_obj: Artifact | None = None

        if not chunks:
            for word in EMPTY_RETRIEVAL_MESSAGE.split(" "):
                token = word + " "
                assistant_tokens.append(token)
                yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"
        else:
            if intent == "essay":
                system_prompt = format_ship30_prompt(sources_context)
            else:
                system_prompt = format_qa_prompt(sources_context)

            try:
                async for token in provider.stream(
                    messages=[LLMMessage(role="user", content=content)],
                    system_prompt=system_prompt,
                ):
                    assistant_tokens.append(token)
                    yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"
            except AppError as exc:
                error_class = exc.code
                err_data = {
                    "error": {"code": exc.code, "message": exc.message, "request_id": request_id},
                    "retryable": exc.status_code in (503, 504),
                }
                yield f"event: error\ndata: {json.dumps(err_data)}\n\n"
            except Exception as exc:
                error_class = "internal_error"
                err_data = {
                    "error": {"code": "internal_error", "message": str(exc), "request_id": request_id},
                    "retryable": False,
                }
                yield f"event: error\ndata: {json.dumps(err_data)}\n\n"

        full_content = "".join(assistant_tokens).strip()
        if not full_content and error_class:
            full_content = "I encountered an error generating an answer. Please check model configuration or try again."

        # Persist assistant message
        assistant_msg = await self._messages.create(
            session_id=session.id,
            role="assistant",
            content=full_content,
            sources=[s.model_dump(mode="json") for s in sources],
            provider=provider.provider_name,
            model=provider.model_name,
            intent=intent,
            error_class=error_class,
        )

        # If essay or artifact and no fatal error, create artifact
        if not error_class and intent in ("essay", "artifact") and full_content:
            art_fmt = artifact_format or ("markdown" if intent == "essay" else "html")
            art_title = _extract_title(full_content, f"Lenny Growth {intent.capitalize()}")
            art_body = full_content
            if art_fmt == "html":
                art_body = sanitize_html(art_body)

            artifact_obj = await self._artifacts.create(
                session_id=session.id,
                message_id=assistant_msg.id,
                client_id=client_id,
                format=art_fmt,
                title=art_title,
                content=art_body,
            )
            assistant_msg.artifact = artifact_obj
            art_payload = {"id": str(artifact_obj.id), "format": art_fmt, "title": art_title}
            yield f"event: artifact\ndata: {json.dumps(art_payload)}\n\n"

        # Update session title and updated_at
        new_title = content[:_TITLE_MAX] if is_first and session.title == "New chat" else None
        await self._sessions.touch(session, title=new_title)

        # 5. Terminal event: done
        done_payload = {
            "assistant_message": MessageRead.model_validate(assistant_msg).model_dump(mode="json"),
            "artifact": ArtifactRead.model_validate(artifact_obj).model_dump(mode="json") if artifact_obj else None,
        }
        yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"
