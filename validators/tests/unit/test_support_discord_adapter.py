from __future__ import annotations

import asyncio
import builtins
from dataclasses import dataclass
import importlib

from creator_engine_validator import support_discord_adapter
from creator_engine_validator.support_runtime import REFUSAL_ANSWER, SupportAnswer


@dataclass(frozen=True)
class Message:
    content: str


class FakeDiscordClient:
    def __init__(self) -> None:
        self.sent: list[tuple[Message, str, object | None]] = []

    async def send_reply(
        self,
        message: Message,
        content: str,
        *,
        allowed_mentions: object | None = None,
    ) -> None:
        self.sent.append((message, content, allowed_mentions))


def _answer(
    answer: str,
    *,
    citations: tuple[str, ...] = (),
    accepted: bool = True,
    reason: str = "cited-corpus-answer",
) -> SupportAnswer:
    return SupportAnswer(
        answer=answer,
        citations=citations,
        accepted=accepted,
        reason=reason,
        model="test-model",
        corpus_sha256="test-corpus",
    )


def test_inbound_message_calls_answer_question_and_renders_citations():
    message = Message("  How do I verify install?  ")
    client = FakeDiscordClient()
    seen: list[str] = []

    def answerer(question: str) -> SupportAnswer:
        seen.append(question)
        return _answer(
            "Run `ce verify-install` after setup.",
            citations=("README.md", "docs/guide/contributing-to-ce.md"),
        )

    asyncio.run(
        support_discord_adapter.handle_message(
            message,
            client,
            answerer=answerer,
        )
    )

    assert seen == ["How do I verify install?"]
    assert len(client.sent) == 1
    _message, reply, allowed_mentions = client.sent[0]
    assert "Run `ce verify-install` after setup." in reply
    assert "Sources:" in reply
    assert "- `README.md`" in reply
    assert "- `docs/guide/contributing-to-ce.md`" in reply
    assert allowed_mentions == support_discord_adapter.EMPTY_ALLOWED_MENTIONS


def test_refusal_renders_refusal_text_without_fabricated_answer():
    message = Message("What is not in the corpus?")
    client = FakeDiscordClient()

    def answerer(_question: str) -> SupportAnswer:
        return _answer(
            REFUSAL_ANSWER,
            accepted=True,
            reason="model-refusal",
        )

    asyncio.run(
        support_discord_adapter.handle_message(
            message,
            client,
            answerer=answerer,
        )
    )

    assert [reply for _message, reply, _allowed_mentions in client.sent] == [REFUSAL_ANSWER]
    assert "Sources:" not in client.sent[0][1]
    assert "install" not in client.sent[0][1].lower()


def test_error_path_sends_safe_reply_without_internal_leak():
    message = Message("Will this crash?")
    client = FakeDiscordClient()

    def answerer(_question: str) -> SupportAnswer:
        raise RuntimeError("secret traceback detail")

    asyncio.run(
        support_discord_adapter.handle_message(
            message,
            client,
            answerer=answerer,
        )
    )

    assert [reply for _message, reply, _allowed_mentions in client.sent] == [
        support_discord_adapter.SAFE_ERROR_REPLY
    ]
    assert "secret" not in client.sent[0][1]
    assert "traceback" not in client.sent[0][1].lower()


def test_long_answers_are_chunked_and_truncated_within_discord_limits():
    message = Message("Explain everything.")
    client = FakeDiscordClient()
    long_answer = "\n\n".join(
        [
            "Paragraph one " + ("alpha " * 80),
            "Paragraph two " + ("bravo " * 80),
            "Paragraph three " + ("charlie " * 80),
        ]
    )

    def answerer(_question: str) -> SupportAnswer:
        return _answer(long_answer, citations=("README.md",))

    asyncio.run(
        support_discord_adapter.handle_message(
            message,
            client,
            answerer=answerer,
            max_message_chars=160,
            max_chunks=3,
        )
    )

    replies = [reply for _message, reply, _allowed_mentions in client.sent]
    assert 1 < len(replies) <= 3
    assert all(len(reply) <= 160 for reply in replies)
    assert support_discord_adapter.TRUNCATION_NOTICE.strip() in "".join(replies)
    assert replies[-1] == "Sources:\n- `README.md`"


def test_no_discord_import_is_required(monkeypatch):
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "discord" or name.startswith("discord."):
            raise AssertionError(f"unexpected Discord import: {name}")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    importlib.reload(support_discord_adapter)
