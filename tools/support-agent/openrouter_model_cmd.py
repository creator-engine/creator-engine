#!/usr/bin/env python3
"""OpenRouter command adapter for CE_SUPPORT_AGENT_MODEL_CMD.

The Creator Engine support runtime writes a JSON ``SupportRequest.to_dict()``
payload to stdin and expects answer text on stdout. This command calls
OpenRouter's chat-completions API and fails closed on any configuration,
transport, HTTP, or response-shape error.

Environment:
  CE_OPENROUTER_API_KEY: required OpenRouter API key.
  CE_OPENROUTER_MODEL: optional model id, default google/gemini-2.5-flash-lite.
  CE_SUPPORT_AGENT_MODEL_TIMEOUT: optional request timeout seconds, default 120.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, TextIO
from urllib import error, request

API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-2.5-flash-lite"
DEFAULT_TIMEOUT_SECONDS = 120.0


class AdapterError(RuntimeError):
    """Expected fail-closed adapter error safe to report on stderr."""


def _timeout() -> float:
    raw = os.environ.get("CE_SUPPORT_AGENT_MODEL_TIMEOUT", "").strip()
    if not raw:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        timeout = float(raw)
    except ValueError as exc:
        raise AdapterError("invalid CE_SUPPORT_AGENT_MODEL_TIMEOUT") from exc
    if timeout <= 0:
        raise AdapterError("CE_SUPPORT_AGENT_MODEL_TIMEOUT must be positive")
    return timeout


def _load_request(stdin: TextIO) -> dict[str, Any]:
    raw = stdin.read()
    if not raw.strip():
        raise AdapterError("empty stdin")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AdapterError("stdin is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise AdapterError("stdin JSON must be an object")
    return payload


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _bundle_context(bundle: Any) -> str:
    if not isinstance(bundle, dict):
        return ""
    blocks: list[str] = []
    for skill in bundle.get("skills") or []:
        if not isinstance(skill, dict):
            continue
        sources = {
            _clean_text(source.get("path"))
            for source in (skill.get("sources") or [])
            if isinstance(source, dict)
        }
        for file_entry in skill.get("files") or []:
            if not isinstance(file_entry, dict):
                continue
            file_path = _clean_text(file_entry.get("path"))
            content = _clean_text(file_entry.get("content"))
            if not file_path or not content:
                continue
            citation = file_path.removeprefix("sources/")
            if sources and citation not in sources:
                continue
            blocks.append(
                "\n".join(
                    [
                        f"Source: {citation}",
                        "Content:",
                        content,
                    ]
                )
            )
    return "\n\n---\n\n".join(blocks)


def _messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    question = _clean_text(payload.get("question"))
    if not question:
        raise AdapterError("request question is required")
    system_prompt = _clean_text(payload.get("system_prompt"))
    context = _bundle_context(payload.get("bundle"))
    user_parts = [
        "Answer the user using only the Creator Engine support corpus below.",
        "If the corpus does not answer the question, answer exactly: I don't know.",
        "When answering, cite exact source paths shown as `Source:` values.",
        "",
        "Question:",
        question,
    ]
    if context:
        user_parts.extend(["", "Support corpus:", context])
    return [
        {
            "role": "system",
            "content": system_prompt
            or "You are a concise Creator Engine support assistant. Cite sources or refuse.",
        },
        {"role": "user", "content": "\n".join(user_parts)},
    ]


def _openrouter_payload(payload: dict[str, Any]) -> bytes:
    model = os.environ.get("CE_OPENROUTER_MODEL", "").strip() or DEFAULT_MODEL
    body = {
        "model": model,
        "messages": _messages(payload),
        "temperature": 0.1,
        "max_tokens": 900,
    }
    return json.dumps(body, separators=(",", ":")).encode("utf-8")


def _extract_answer(response_body: bytes) -> str:
    try:
        parsed = json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdapterError("OpenRouter response was not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise AdapterError("OpenRouter response JSON was not an object")
    choices = parsed.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AdapterError("OpenRouter response had no choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise AdapterError("OpenRouter choice was malformed")
    message = first.get("message")
    if not isinstance(message, dict):
        raise AdapterError("OpenRouter choice had no message")
    answer = _clean_text(message.get("content"))
    if not answer:
        raise AdapterError("OpenRouter response content was empty")
    return answer


def _call_openrouter(payload: dict[str, Any]) -> str:
    api_key = os.environ.get("CE_OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise AdapterError("CE_OPENROUTER_API_KEY is required")
    req = request.Request(
        API_URL,
        data=_openrouter_payload(payload),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=_timeout()) as response:
            status = int(getattr(response, "status", 200))
            body = response.read()
    except error.HTTPError as exc:
        raise AdapterError(f"OpenRouter HTTP error: {exc.code}") from exc
    except error.URLError as exc:
        raise AdapterError(f"OpenRouter request failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise AdapterError("OpenRouter request timed out") from exc

    if status < 200 or status >= 300:
        raise AdapterError(f"OpenRouter HTTP error: {status}")
    return _extract_answer(body)


def main(
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    try:
        payload = _load_request(stdin)
        answer = _call_openrouter(payload)
    except AdapterError as exc:
        print(f"openrouter_model_cmd: {exc}", file=stderr)
        return 1
    print(answer, file=stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
