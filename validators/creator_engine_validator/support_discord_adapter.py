"""Discord channel adapter for the support-agent runtime.

This module is intentionally transport-thin and dependency-free. A future live
Discord binding can adapt a discord.py client to ``DiscordChannelClient`` and
hand messages to ``handle_message`` or ``serve``; this file does not import or
configure any provider client.
"""
from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Protocol

DISCORD_MESSAGE_LIMIT = 2000
DEFAULT_MESSAGE_LIMIT = 1900
DEFAULT_MAX_CHUNKS = 4
EMPTY_ALLOWED_MENTIONS = {"parse": []}
REFUSAL_ANSWER = "I don't know"
SAFE_ERROR_REPLY = "I couldn't answer that right now."
TRUNCATION_NOTICE = "\n\n[response truncated]"


class DiscordInboundMessage(Protocol):
    """Minimal inbound message shape consumed by the adapter."""

    content: str


class DiscordChannelClient(Protocol):
    """Injected Discord transport boundary.

    Concrete clients own provider auth, gateway setup, event subscription, and
    network I/O. The adapter only receives message-like objects and asks the
    client to send replies.
    """

    def receive_messages(self) -> AsyncIterator[DiscordInboundMessage]:
        ...

    async def send_reply(
        self,
        message: DiscordInboundMessage,
        content: str,
        *,
        allowed_mentions: object | None = None,
    ) -> None:
        ...


class SupportAnswerLike(Protocol):
    """Structural subset of ``support_runtime.SupportAnswer`` used here."""

    answer: str
    citations: tuple[str, ...]
    accepted: bool
    reason: str
    model: str
    corpus_sha256: str
    token_spend: int | float | None


AnswerQuestion = Callable[[str], SupportAnswerLike]


def extract_question(message: DiscordInboundMessage) -> str:
    """Return the user question from a Discord-like inbound message."""

    content = getattr(message, "content", "")
    if not isinstance(content, str):
        return ""
    return content.strip()


def render_discord_reply(
    answer: SupportAnswerLike,
    *,
    max_message_chars: int = DEFAULT_MESSAGE_LIMIT,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
) -> tuple[str, ...]:
    """Render a validated ``SupportAnswer`` into Discord-safe message chunks."""

    limit = _message_limit(max_message_chars)
    chunk_count = max(1, int(max_chunks))
    text = _answer_text(answer)

    if _has_cited_answer(answer, text):
        sources = _sources_block(answer.citations, max_message_chars=limit)
        return _chunk_cited_answer(
            text,
            sources,
            max_message_chars=limit,
            max_chunks=chunk_count,
        )

    return _chunk_text(text, max_message_chars=limit, max_chunks=chunk_count)


async def handle_message(
    message: DiscordInboundMessage,
    client: DiscordChannelClient,
    *,
    answerer: AnswerQuestion | None = None,
    max_message_chars: int = DEFAULT_MESSAGE_LIMIT,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
) -> None:
    """Answer one inbound Discord message and send safe replies.

    Runtime and rendering errors are normalized to ``SAFE_ERROR_REPLY``. Send
    failures are swallowed because the adapter has no second channel available
    for a safe report.
    """

    try:
        question = extract_question(message)
        if answerer is None:
            answerer = _default_answer_question
        answer = answerer(question)
        replies = render_discord_reply(
            answer,
            max_message_chars=max_message_chars,
            max_chunks=max_chunks,
        )
    except Exception:
        replies = (SAFE_ERROR_REPLY,)

    for reply in replies:
        try:
            await client.send_reply(
                message,
                reply,
                allowed_mentions=EMPTY_ALLOWED_MENTIONS,
            )
        except Exception:
            return


async def serve(
    client: DiscordChannelClient,
    *,
    answerer: AnswerQuestion | None = None,
    max_message_chars: int = DEFAULT_MESSAGE_LIMIT,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
) -> None:
    """Consume messages from an injected client until its iterator ends."""

    async for message in client.receive_messages():
        await handle_message(
            message,
            client,
            answerer=answerer,
            max_message_chars=max_message_chars,
            max_chunks=max_chunks,
        )


def _default_answer_question(question: str) -> SupportAnswerLike:
    runtime = __import__(
        "creator_engine_validator.support_runtime",
        fromlist=["answer_question"],
    )
    return runtime.answer_question(question)


def _answer_text(answer: SupportAnswerLike) -> str:
    clean = answer.answer.strip()
    return clean or REFUSAL_ANSWER


def _has_cited_answer(answer: SupportAnswerLike, text: str) -> bool:
    return bool(answer.accepted and answer.citations and text != REFUSAL_ANSWER)


def _sources_block(citations: tuple[str, ...], *, max_message_chars: int) -> str:
    lines = ["Sources:"]
    for citation in citations:
        candidate = [*lines, f"- `{citation}`"]
        rendered = "\n".join(candidate)
        if len(rendered) > max_message_chars:
            break
        lines = candidate
    return "\n".join(lines)


def _chunk_cited_answer(
    answer_text: str,
    sources: str,
    *,
    max_message_chars: int,
    max_chunks: int,
) -> tuple[str, ...]:
    separator = "\n\n"
    rendered = f"{answer_text}{separator}{sources}"
    if len(rendered) <= max_message_chars:
        return (rendered,)

    if max_chunks == 1:
        answer_budget = max_message_chars - len(separator) - len(sources) - len(TRUNCATION_NOTICE)
        if answer_budget < 1:
            return (_chunk_text(sources, max_message_chars=max_message_chars, max_chunks=1)[0],)
        trimmed = answer_text[:answer_budget].rstrip()
        return (f"{trimmed}{TRUNCATION_NOTICE}{separator}{sources}",)

    answer_chunk_count = max_chunks - 1
    answer_budget = (max_message_chars * answer_chunk_count) - len(TRUNCATION_NOTICE)
    if len(answer_text) > answer_budget:
        answer_text = f"{answer_text[:answer_budget].rstrip()}{TRUNCATION_NOTICE}"

    answer_chunks = _chunk_text(
        answer_text,
        max_message_chars=max_message_chars,
        max_chunks=answer_chunk_count,
    )
    return (*answer_chunks, sources)


def _message_limit(value: int) -> int:
    try:
        requested = int(value)
    except (TypeError, ValueError):
        requested = DEFAULT_MESSAGE_LIMIT
    return max(1, min(DISCORD_MESSAGE_LIMIT, requested))


def _chunk_text(
    text: str,
    *,
    max_message_chars: int,
    max_chunks: int,
) -> tuple[str, ...]:
    if len(text) <= max_message_chars:
        return (text,)

    chunks: list[str] = []
    remaining = text.strip()
    while remaining and len(chunks) < max_chunks:
        if len(remaining) <= max_message_chars:
            chunks.append(remaining)
            remaining = ""
            break
        split_at = _best_split(remaining, max_message_chars)
        chunk = remaining[:split_at].rstrip()
        chunks.append(chunk or remaining[:max_message_chars])
        remaining = remaining[split_at:].lstrip()

    if remaining and chunks:
        notice = TRUNCATION_NOTICE
        last_budget = max_message_chars - len(notice)
        if last_budget > 0:
            chunks[-1] = f"{chunks[-1][:last_budget].rstrip()}{notice}"
        else:
            chunks[-1] = notice[:max_message_chars]

    return tuple(chunks or [REFUSAL_ANSWER])


def _best_split(text: str, max_message_chars: int) -> int:
    for separator in ("\n\n", "\n", " "):
        index = text.rfind(separator, 0, max_message_chars + 1)
        if index > 0:
            return index + len(separator)
    return max_message_chars


__all__ = [
    "DEFAULT_MAX_CHUNKS",
    "DEFAULT_MESSAGE_LIMIT",
    "DISCORD_MESSAGE_LIMIT",
    "EMPTY_ALLOWED_MENTIONS",
    "SAFE_ERROR_REPLY",
    "TRUNCATION_NOTICE",
    "AnswerQuestion",
    "DiscordChannelClient",
    "DiscordInboundMessage",
    "extract_question",
    "handle_message",
    "render_discord_reply",
    "serve",
]
