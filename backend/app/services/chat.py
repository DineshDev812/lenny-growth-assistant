from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agent.prompts import format_qa_prompt
from app.agent.router import classify_intent
from app.agent.skills.ship30.prompts import format_ship30_prompt
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AppError,
    ModelTimeoutError,
    ModelUnavailableError,
    NotFoundError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUnconfiguredError,
)
from app.db.models import Artifact, Message, Session
from app.db.session import SessionLocal
from app.llm.anthropic import AnthropicProvider
from app.llm.base import BaseLLMProvider, LLMMessage
from app.llm.factory import get_llm_provider
from app.llm.ollama import OllamaProvider
from app.repositories.artifacts import ArtifactRepository
from app.repositories.messages import MessageRepository
from app.repositories.sessions import SessionRepository
from app.schemas.artifacts import ArtifactRead
from app.schemas.messages import MessageRead, SendMessageResponse, Source
from app.services.grounding import (
    _CITATION_GROUP_RE,
    filter_cited_sources,
    format_source_context,
    validate_citations,
)
from app.services.query_builder import build_retrieval_query
from app.services.retrieval import RetrievalService
from app.services.sanitizer import extract_artifact_content, sanitize_html

logger = logging.getLogger(__name__)

EMPTY_RETRIEVAL_MESSAGE = (
    "The transcripts I have don't support an answer to this. "
    "Try asking about a product, growth, or career topic covered on Lenny's Podcast."
)

_TITLE_MAX = 60


def _extract_title(text: str, fallback: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        first = lines[0].lstrip("#").strip()
        if 5 < len(first) <= 80:
            return first
    return fallback


def _prepare_history_context(
    messages: list[Message],
    max_history: int,
    token_budget: int = 1500,
) -> list[LLMMessage]:
    """Prepare prior conversation history for model context:
    1. Take the last `max_history` messages.
    2. Strip old [S#] markers from past assistant messages.
    3. Ensure roles alternate and start with 'user'.
    4. Stay within token budget.
    """
    if not messages or max_history <= 0:
        return []

    recent = messages[-max_history:]
    cleaned_items: list[tuple[str, str]] = []

    for msg in recent:
        text = msg.content.strip()
        if msg.role == "assistant":
            # Strip old citation markers like [S1], [S2, S3]
            text = _CITATION_GROUP_RE.sub("", text)
            text = re.sub(r"  +", " ", text).strip()
        if text:
            cleaned_items.append((msg.role, text))

    # Anthropic requirement: must start with 'user'
    while cleaned_items and cleaned_items[0][0] != "user":
        cleaned_items.pop(0)

    # Ensure alternating roles: if two consecutive have the same role, combine them
    alternated: list[tuple[str, str]] = []
    for role, text in cleaned_items:
        if alternated and alternated[-1][0] == role:
            prev_role, prev_text = alternated.pop()
            alternated.append((role, f"{prev_text}\n\n{text}"))
        else:
            alternated.append((role, text))

    # Token budget trimming
    llm_messages: list[LLMMessage] = []
    total_tokens = 0
    # Process from newest to oldest to fit budget
    for role, text in reversed(alternated):
        est_tokens = len(text) // 4 + 10
        if total_tokens + est_tokens > token_budget and llm_messages:
            break
        llm_messages.insert(0, LLMMessage(role=role, content=text))
        total_tokens += est_tokens

    # Again ensure starts with 'user' after potential budget cut
    while llm_messages and llm_messages[0].role != "user":
        llm_messages.pop(0)

    return llm_messages


def _build_fallback_provider(settings: Settings) -> BaseLLMProvider | None:
    fb = (settings.model_fallback or "none").lower().strip()
    if fb == "none" or fb == settings.model_provider:
        return None
    if fb == "anthropic":
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            timeout=settings.llm_timeout_seconds,
        )
    if fb == "ollama":
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout=settings.llm_timeout_seconds,
        )
    return None


class ChatService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        db: AsyncSession | None = None,
    ) -> None:
        if session_factory is not None:
            self._session_factory = session_factory
        elif db is not None:
            # Create a sessionmaker bound to the existing engine
            self._session_factory = async_sessionmaker(
                db.bind, expire_on_commit=False, class_=AsyncSession
            )
        else:
            self._session_factory = SessionLocal

    async def send_message_sync(
        self,
        *,
        session_id: UUID,
        client_id: UUID,
        content: str,
        explicit_intent: str | None = None,
        artifact_format: str | None = None,
    ) -> SendMessageResponse:
        settings = get_settings()
        intent = classify_intent(content, explicit_intent)

        # -------------------------------------------------------------
        # Phase A (own session, commit): Verify ownership & save user message
        # -------------------------------------------------------------
        async with self._session_factory() as db_a:
            sess_repo = SessionRepository(db_a)
            session = await sess_repo.get_owned(session_id, client_id)
            if session is None:
                raise NotFoundError("Session not found.")
            is_first = len(session.messages) == 0

            msg_repo = MessageRepository(db_a)
            user_msg = await msg_repo.create(
                session_id=session.id,
                role="user",
                content=content,
                sources=[],
                intent=intent,
            )
            await db_a.commit()
            user_msg_id = user_msg.id

        # -------------------------------------------------------------
        # Phase B (own session, read-only, CLOSE before LLM): History & Retrieval
        # -------------------------------------------------------------
        async with self._session_factory() as db_b:
            sess_repo = SessionRepository(db_b)
            session = await sess_repo.get_owned(session_id, client_id)
            if session is None:
                raise NotFoundError("Session not found.")

            # Load history excluding the user message just inserted
            prior_messages = [m for m in session.messages if m.id != user_msg_id]
            prev_user_msg = next((m for m in reversed(prior_messages) if m.role == "user"), None)
            history_context = _prepare_history_context(
                prior_messages,
                max_history=settings.chat_history_messages,
                token_budget=1000,
            )

            # Query enrichment for follow-ups
            retrieval_query = build_retrieval_query(
                content,
                previous_user_message=prev_user_msg.content if prev_user_msg else None,
            )

            retrieval_service = RetrievalService(db_b)
            chunks, match_mode = await retrieval_service.retrieve_with_meta(
                retrieval_query, k=4 if intent == "qa" else 6
            )

        # -------------------------------------------------------------
        # Model generation & Grounding (No DB connection held!)
        # -------------------------------------------------------------
        primary_provider = get_llm_provider(settings)
        active_provider = primary_provider

        # Check weak OR-fallback threshold or empty retrieval
        should_abstain = False
        if not chunks:
            should_abstain = True
        elif match_mode == "or_fallback":
            highest_score = max((c.score for c in chunks), default=0.0)
            if highest_score < settings.retrieval_min_answer_score:
                logger.info(
                    "OR-fallback score below minimum threshold, abstaining without LLM call",
                    extra={
                        "event": "weak_retrieval_abstain",
                        "highest_score": highest_score,
                        "threshold": settings.retrieval_min_answer_score,
                    },
                )
                should_abstain = True

        raw_content = ""
        error_class: str | None = None
        sources: list[Source] = []

        if should_abstain:
            raw_content = EMPTY_RETRIEVAL_MESSAGE
            sources = []
        else:
            sources, sources_context = format_source_context(
                chunks,
                token_budget=settings.context_token_budget,
                max_chunks_per_episode=2,
            )
            if intent == "essay":
                system_prompt = format_ship30_prompt(sources_context)
            else:
                system_prompt = format_qa_prompt(sources_context)

            all_messages = [*history_context, LLMMessage(role="user", content=content)]
            gen_tokens = 2000 if intent == "essay" else (1200 if intent == "artifact" else 450)

            try:
                llm_res = await asyncio.wait_for(
                    primary_provider.generate(
                        messages=all_messages,
                        system_prompt=system_prompt,
                        max_tokens=gen_tokens,
                    ),
                    timeout=settings.llm_timeout_seconds,
                )
                raw_content = llm_res.content
            except (ProviderTimeoutError, asyncio.TimeoutError) as exc:
                fallback_provider = _build_fallback_provider(settings)
                if fallback_provider:
                    logger.info("Primary timed out, attempting fallback", extra={"event": "model_fallback"})
                    try:
                        active_provider = fallback_provider
                        llm_res = await asyncio.wait_for(
                            fallback_provider.generate(
                                messages=all_messages,
                                system_prompt=system_prompt,
                                max_tokens=gen_tokens,
                            ),
                            timeout=settings.llm_timeout_seconds,
                        )
                        raw_content = llm_res.content
                    except Exception as fb_exc:
                        logger.warning("Fallback model also failed: %s", fb_exc)
                        raise ModelTimeoutError("Model request timed out.") from fb_exc
                else:
                    raise ModelTimeoutError("Model request timed out.") from exc
            except (ProviderUnavailableError, ProviderUnconfiguredError) as exc:
                fallback_provider = _build_fallback_provider(settings)
                if fallback_provider:
                    logger.info("Primary unavailable, attempting fallback", extra={"event": "model_fallback"})
                    try:
                        active_provider = fallback_provider
                        llm_res = await asyncio.wait_for(
                            fallback_provider.generate(
                                messages=all_messages,
                                system_prompt=system_prompt,
                            ),
                            timeout=settings.llm_timeout_seconds,
                        )
                        raw_content = llm_res.content
                    except Exception as fb_exc:
                        logger.warning("Fallback model also failed: %s", fb_exc)
                        raise ModelUnavailableError("Model provider is unavailable.") from fb_exc
                else:
                    raise ModelUnavailableError("Model provider is unavailable.") from exc

        # Citation validation and strict grounding
        final_content = raw_content
        persisted_sources: list[Source] = []

        if sources and not should_abstain:
            clean_text, used_ids, dropped_ids = validate_citations(raw_content, sources)
            if settings.grounding_strict and not used_ids:
                logger.info(
                    "Strict grounding failed: answer produced zero valid citations",
                    extra={"event": "grounding_failed", "dropped_citations": dropped_ids},
                )
                final_content = EMPTY_RETRIEVAL_MESSAGE
                error_class = "grounding_failed"
                persisted_sources = []
            else:
                final_content = clean_text
                persisted_sources = filter_cited_sources(sources, used_ids)
        elif should_abstain:
            persisted_sources = []

        # -------------------------------------------------------------
        # Phase C (own session, commit): Save assistant message & artifact
        # -------------------------------------------------------------
        async with self._session_factory() as db_c:
            sess_repo = SessionRepository(db_c)
            session = await sess_repo.get_owned(session_id, client_id)
            if session is None:
                raise NotFoundError("Session not found.")

            msg_repo = MessageRepository(db_c)
            art_repo = ArtifactRepository(db_c)

            assistant_msg = await msg_repo.create(
                session_id=session.id,
                role="assistant",
                content=final_content,
                sources=[s.model_dump(mode="json") for s in persisted_sources],
                provider=active_provider.provider_name,
                model=active_provider.model_name,
                intent=intent,
                error_class=error_class,
            )

            artifact_obj: Artifact | None = None
            if not error_class and intent in ("essay", "artifact") and final_content:
                art_fmt = artifact_format or ("markdown" if intent == "essay" else "html")
                art_title = _extract_title(final_content, f"Lenny Growth {intent.capitalize()}")
                art_body = extract_artifact_content(final_content, art_fmt)

                artifact_obj = await art_repo.create(
                    session_id=session.id,
                    message_id=assistant_msg.id,
                    client_id=client_id,
                    format=art_fmt,
                    title=art_title,
                    content=art_body,
                )
                assistant_msg.artifact = artifact_obj

            new_title = content[:_TITLE_MAX] if is_first and session.title == "New chat" else None
            await sess_repo.touch(session, title=new_title)
            await db_c.commit()

            # Refresh objects for serialization
            user_msg_final = await msg_repo._db.get(Message, user_msg_id)

        return SendMessageResponse(
            user_message=MessageRead.model_validate(user_msg_final),
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
        settings = get_settings()
        intent = classify_intent(content, explicit_intent)

        # -------------------------------------------------------------
        # Phase A (own session, commit): Verify ownership & save user message
        # -------------------------------------------------------------
        async with self._session_factory() as db_a:
            sess_repo = SessionRepository(db_a)
            session = await sess_repo.get_owned(session_id, client_id)
            if session is None:
                raise NotFoundError("Session not found.")
            is_first = len(session.messages) == 0

            msg_repo = MessageRepository(db_a)
            user_msg = await msg_repo.create(
                session_id=session.id,
                role="user",
                content=content,
                sources=[],
                intent=intent,
            )
            await db_a.commit()
            user_msg_id = user_msg.id

        primary_provider = get_llm_provider(settings)
        active_provider = primary_provider

        # 1. Event: start
        start_payload = {
            "user_message_id": str(user_msg_id),
            "intent": intent,
            "provider": primary_provider.provider_name,
            "model": primary_provider.model_name,
        }
        yield f"event: start\ndata: {json.dumps(start_payload)}\n\n"

        # -------------------------------------------------------------
        # Phase B (own session, read-only, CLOSE before LLM): History & Retrieval
        # -------------------------------------------------------------
        async with self._session_factory() as db_b:
            sess_repo = SessionRepository(db_b)
            session = await sess_repo.get_owned(session_id, client_id)
            if session is None:
                raise NotFoundError("Session not found.")

            prior_messages = [m for m in session.messages if m.id != user_msg_id]
            prev_user_msg = next((m for m in reversed(prior_messages) if m.role == "user"), None)
            history_context = _prepare_history_context(
                prior_messages,
                max_history=settings.chat_history_messages,
                token_budget=1000,
            )

            retrieval_query = build_retrieval_query(
                content,
                previous_user_message=prev_user_msg.content if prev_user_msg else None,
            )

            retrieval_service = RetrievalService(db_b)
            chunks, match_mode = await retrieval_service.retrieve_with_meta(
                retrieval_query, k=4 if intent == "qa" else 6
            )

        # Format retrieved sources
        sources, sources_context = format_source_context(
            chunks,
            token_budget=settings.context_token_budget,
            max_chunks_per_episode=2,
        )

        # 2. Event: sources (emit all retrieved sources to frontend)
        yield f"event: sources\ndata: {json.dumps({'sources': [s.model_dump(mode='json') for s in sources]})}\n\n"

        # Check weak OR-fallback threshold or empty retrieval
        should_abstain = False
        if not chunks:
            should_abstain = True
        elif match_mode == "or_fallback":
            highest_score = max((c.score for c in chunks), default=0.0)
            if highest_score < settings.retrieval_min_answer_score:
                logger.info(
                    "OR-fallback score below minimum threshold, abstaining without LLM call",
                    extra={
                        "event": "weak_retrieval_abstain",
                        "highest_score": highest_score,
                        "threshold": settings.retrieval_min_answer_score,
                    },
                )
                should_abstain = True

        assistant_tokens: list[str] = []
        error_class: str | None = None

        if should_abstain:
            for word in EMPTY_RETRIEVAL_MESSAGE.split(" "):
                token = word + " "
                assistant_tokens.append(token)
                yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"
        else:
            gen_tokens = 2000 if intent == "essay" else (1200 if intent == "artifact" else 450)
            if intent == "essay":
                system_prompt = format_ship30_prompt(sources_context)
            else:
                system_prompt = format_qa_prompt(sources_context)

            all_messages = [*history_context, LLMMessage(role="user", content=content)]

            try:
                # 3. Stream from model with first-token timeout, fallback, and total timeout
                first_token_timeout = settings.llm_first_token_timeout_seconds
                total_timeout = settings.llm_timeout_seconds
                stream_start = time.monotonic()

                stream_iter = primary_provider.stream(
                    messages=all_messages,
                    system_prompt=system_prompt,
                    max_tokens=gen_tokens,
                )

                first_token = None
                try:
                    first_token = await asyncio.wait_for(
                        stream_iter.__anext__(),
                        timeout=first_token_timeout,
                    )
                except (ProviderTimeoutError, ProviderUnavailableError, ProviderUnconfiguredError, asyncio.TimeoutError) as first_err:
                    fallback_provider = _build_fallback_provider(settings)
                    if fallback_provider:
                        logger.info("Primary stream failed on first token, attempting fallback", extra={"event": "stream_fallback"})
                        active_provider = fallback_provider
                        stream_iter = fallback_provider.stream(
                            messages=all_messages,
                            system_prompt=system_prompt,
                            max_tokens=gen_tokens,
                        )
                        first_token = await asyncio.wait_for(
                            stream_iter.__anext__(),
                            timeout=first_token_timeout,
                        )
                    else:
                        raise first_err

                if first_token is not None:
                    assistant_tokens.append(first_token)
                    yield f"event: token\ndata: {json.dumps({'text': first_token})}\n\n"

                # Subsequent tokens under total timeout deadline
                deadline = stream_start + total_timeout
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise ModelTimeoutError("Stream exceeded overall timeout.")
                    try:
                        token = await asyncio.wait_for(
                            stream_iter.__anext__(),
                            timeout=min(remaining, 30.0),
                        )
                        assistant_tokens.append(token)
                        yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"
                    except StopAsyncIteration:
                        break

            except asyncio.CancelledError:
                # Client disconnected mid-stream
                logger.info(
                    "Client disconnected mid-stream",
                    extra={"event": "client_disconnected", "session_id": str(session_id)},
                )
                partial_content = "".join(assistant_tokens).strip() or "[Client disconnected]"
                async with self._session_factory() as db_disc:
                    m_repo = MessageRepository(db_disc)
                    s_repo = SessionRepository(db_disc)
                    await m_repo.create(
                        session_id=session_id,
                        role="assistant",
                        content=partial_content,
                        sources=[],
                        provider=active_provider.provider_name,
                        model=active_provider.model_name,
                        intent=intent,
                        error_class="client_disconnected",
                    )
                    s_obj = await s_repo.get_owned(session_id, client_id)
                    if s_obj:
                        await s_repo.touch(s_obj)
                    await db_disc.commit()
                raise

            except (ProviderTimeoutError, ModelTimeoutError, asyncio.TimeoutError) as exc:
                error_class = "model_timeout"
                logger.warning("Streaming model timeout: %s", exc, extra={"event": "model_timeout", "request_id": request_id})
                err_data = {
                    "error": {"code": "model_timeout", "message": "Model request timed out.", "request_id": request_id},
                    "retryable": True,
                }
                yield f"event: error\ndata: {json.dumps(err_data)}\n\n"

            except (ProviderUnavailableError, ProviderUnconfiguredError, ModelUnavailableError) as exc:
                error_class = "model_unavailable"
                logger.warning("Streaming model unavailable: %s", exc, extra={"event": "model_unavailable", "request_id": request_id})
                err_data = {
                    "error": {"code": "model_unavailable", "message": "Model provider is currently unavailable.", "request_id": request_id},
                    "retryable": True,
                }
                yield f"event: error\ndata: {json.dumps(err_data)}\n\n"

            except Exception as exc:
                error_class = "internal_error"
                logger.exception("Unexpected error during stream: %s", exc, extra={"event": "internal_error", "request_id": request_id})
                err_data = {
                    "error": {"code": "internal_error", "message": "An unexpected error occurred.", "request_id": request_id},
                    "retryable": False,
                }
                yield f"event: error\ndata: {json.dumps(err_data)}\n\n"

        raw_content = "".join(assistant_tokens).strip()
        if not raw_content and error_class:
            raw_content = "I encountered an error generating an answer. Please check model configuration or try again."

        # Citation validation and strict grounding
        final_content = raw_content
        persisted_sources: list[Source] = []

        if sources and not should_abstain and not error_class:
            clean_text, used_ids, dropped_ids = validate_citations(raw_content, sources)
            if settings.grounding_strict and not used_ids:
                logger.info(
                    "Strict grounding failed: answer produced zero valid citations",
                    extra={"event": "grounding_failed", "dropped_citations": dropped_ids},
                )
                final_content = EMPTY_RETRIEVAL_MESSAGE
                error_class = "grounding_failed"
                persisted_sources = []
            else:
                final_content = clean_text
                persisted_sources = filter_cited_sources(sources, used_ids)
        elif should_abstain:
            persisted_sources = []

        # -------------------------------------------------------------
        # Phase C (own session, commit): Save assistant message & artifact
        # -------------------------------------------------------------
        artifact_obj: Artifact | None = None
        async with self._session_factory() as db_c:
            sess_repo = SessionRepository(db_c)
            session = await sess_repo.get_owned(session_id, client_id)
            if session is None:
                raise NotFoundError("Session not found.")

            msg_repo = MessageRepository(db_c)
            art_repo = ArtifactRepository(db_c)

            assistant_msg = await msg_repo.create(
                session_id=session.id,
                role="assistant",
                content=final_content,
                sources=[s.model_dump(mode="json") for s in persisted_sources],
                provider=active_provider.provider_name,
                model=active_provider.model_name,
                intent=intent,
                error_class=error_class,
            )

            # 4. Event: artifact
            if not error_class and intent in ("essay", "artifact") and final_content:
                art_fmt = artifact_format or ("markdown" if intent == "essay" else "html")
                art_title = _extract_title(final_content, f"Lenny Growth {intent.capitalize()}")
                art_body = extract_artifact_content(final_content, art_fmt)

                artifact_obj = await art_repo.create(
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

            new_title = content[:_TITLE_MAX] if is_first and session.title == "New chat" else None
            await sess_repo.touch(session, title=new_title)
            await db_c.commit()

        # 5. Terminal event: done
        done_payload = {
            "assistant_message": MessageRead.model_validate(assistant_msg).model_dump(mode="json"),
            "artifact": ArtifactRead.model_validate(artifact_obj).model_dump(mode="json") if artifact_obj else None,
        }
        yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"
