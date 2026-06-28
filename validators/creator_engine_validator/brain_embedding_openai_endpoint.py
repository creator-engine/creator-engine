"""OpenAI-compatible HTTP endpoint embedder adapter for brain recall.

Supports any server that implements the OpenAI /v1/embeddings API, including
local vLLM serving (e.g. Qwen3-Embedding-8B at http://127.0.0.1:8989).

Design invariants
-----------------
* ``requires_egress = False`` for localhost (127.0.0.1 / ::1) endpoints — a
  local vLLM serve is not external egress.  External URLs set it True so the
  ``require_embedding_allowed`` gate in ``brain_recall`` continues to enforce the
  confidentiality guard for real remote endpoints.
* All heavy I/O (urllib.request) is imported lazily so the module stays importable
  in dependency-free CI environments without network access.
* The adapter is dependency-free beyond the Python standard library: urllib.request
  + json, no ``requests``, no ``httpx``, no ``openai`` SDK.
"""

from __future__ import annotations

import json
import math
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from creator_engine_validator.brain_recall import Vector

DEFAULT_ENDPOINT = "http://127.0.0.1:8989/v1/embeddings"
DEFAULT_MODEL_ID = "Qwen/Qwen3-Embedding-8B"
DEFAULT_DIM = 4096
DEFAULT_TIMEOUT_SECONDS = 60
# Conservative per-request batch size (in texts).  Qwen3-Embedding-8B has an
# 8192-token context window; large chunks can overflow it when sent in bulk.
# A batch of 32 texts keeps the per-request token budget safe for typical
# markdown memory-file chunks while still amortising HTTP round-trip overhead.
DEFAULT_BATCH_SIZE = 32

_LOCALHOST_HOSTS = {"127.0.0.1", "::1", "localhost"}


class BrainEmbeddingEndpointError(Exception):
    code = "CE-BRAIN-EMBEDDING-ENDPOINT-ERROR"


class BrainEmbeddingEndpointUnavailable(BrainEmbeddingEndpointError):
    code = "CE-BRAIN-EMBEDDING-ENDPOINT-UNAVAILABLE"


class BrainEmbeddingEndpointInvalid(BrainEmbeddingEndpointError):
    code = "CE-BRAIN-EMBEDDING-ENDPOINT-INVALID"


@dataclass
class OpenAIEndpointEmbeddingAdapter:
    """EmbeddingAdapter backed by an OpenAI-compatible /v1/embeddings HTTP endpoint.

    Parameters
    ----------
    endpoint:
        Full URL of the embeddings endpoint (default: ``http://127.0.0.1:8989/v1/embeddings``).
    model_id:
        Model name sent in the ``model`` field of every request (default: ``Qwen/Qwen3-Embedding-8B``).
    dim:
        Expected embedding dimension. Validated against the server response.
    timeout:
        HTTP request timeout in seconds (default: 60 s).
    api_key:
        Optional Bearer token for authenticated endpoints (not needed for local vLLM).
    _http_get:
        Injection point for tests — if supplied it must be a callable
        ``(url: str, payload: dict) -> list[list[float]]`` that returns the raw
        embedding rows.  When ``None`` (the default) the adapter uses
        ``urllib.request``.
    """

    endpoint: str = DEFAULT_ENDPOINT
    model_id: str = DEFAULT_MODEL_ID
    dim: int = DEFAULT_DIM
    timeout: int = DEFAULT_TIMEOUT_SECONDS
    api_key: str | None = None
    batch_size: int = DEFAULT_BATCH_SIZE
    requires_egress: bool = field(default=False, init=False)
    _http_get: Any | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.endpoint, str) or not self.endpoint.strip():
            raise BrainEmbeddingEndpointInvalid("endpoint must be a non-empty string URL")
        self.endpoint = self.endpoint.strip()
        if not isinstance(self.model_id, str) or not self.model_id.strip():
            raise BrainEmbeddingEndpointInvalid("model_id must be a non-empty string")
        self.model_id = self.model_id.strip()
        if not isinstance(self.dim, int) or self.dim <= 0:
            raise BrainEmbeddingEndpointInvalid("dim must be a positive integer")
        if not isinstance(self.timeout, int) or self.timeout <= 0:
            raise BrainEmbeddingEndpointInvalid("timeout must be a positive integer (seconds)")
        if not isinstance(self.batch_size, int) or self.batch_size <= 0:
            raise BrainEmbeddingEndpointInvalid("batch_size must be a positive integer")
        # Determine egress: localhost endpoints are local-only (no external egress).
        self.requires_egress = not _is_localhost_endpoint(self.endpoint)

    def with_http_getter(self, getter: Any) -> "OpenAIEndpointEmbeddingAdapter":
        """Return a copy of this adapter with an injected HTTP getter (for tests)."""

        clone = OpenAIEndpointEmbeddingAdapter(
            endpoint=self.endpoint,
            model_id=self.model_id,
            dim=self.dim,
            timeout=self.timeout,
            api_key=self.api_key,
            batch_size=self.batch_size,
        )
        clone._http_get = getter
        return clone

    def embed(self, texts: Sequence[str]) -> tuple[Vector, ...]:
        """Embed ``texts`` via the configured /v1/embeddings endpoint.

        Each text is pre-truncated to ``max_chars`` (default 16 000) before
        sending, so no individual request can exceed the model's 8 192-token
        context window.  Texts are then split into ``batch_size``-sized requests
        to amortise HTTP round-trip overhead.  Validates that each returned vector
        has exactly ``self.dim`` finite floats.
        """

        values = _validate_texts(texts)
        if not values:
            return ()

        # Pre-truncate every text before batching so individual oversized chunks
        # never reach the HTTP layer (avoids 400 errors and the costly recursive
        # retry path).
        safe_values = tuple(_truncate_text(t) for t in values)

        all_rows: list[Any] = []
        for start in range(0, len(safe_values), self.batch_size):
            batch = list(safe_values[start : start + self.batch_size])
            rows = self._fetch_embeddings(batch)
            all_rows.extend(rows)

        return _parse_rows(all_rows, count=len(values), expected_dim=self.dim)

    # -- internals -------------------------------------------------------------

    def _fetch_embeddings(self, texts: list[str]) -> list[Any]:
        payload = {"model": self.model_id, "input": texts}
        if self._http_get is not None:
            return self._http_get(self.endpoint, payload)
        try:
            return _http_post_embeddings(
                self.endpoint, payload, timeout=self.timeout, api_key=self.api_key
            )
        except BrainEmbeddingEndpointUnavailable as exc:
            # 400 usually means one or more texts exceeded the model token limit.
            # If we already have a single text, truncate it and retry once.
            if len(texts) == 1 and "400" in str(exc):
                truncated = _truncate_text(texts[0])
                return _http_post_embeddings(
                    self.endpoint,
                    {"model": self.model_id, "input": [truncated]},
                    timeout=self.timeout,
                    api_key=self.api_key,
                )
            # Multiple texts: split the batch in half and recurse.
            if len(texts) > 1 and "400" in str(exc):
                mid = len(texts) // 2
                left = self._fetch_embeddings(texts[:mid])
                right = self._fetch_embeddings(texts[mid:])
                return left + right
            raise


def _is_localhost_endpoint(url: str) -> bool:
    """Return True when the URL resolves to a loopback address (no external egress)."""

    try:
        import urllib.parse

        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname or ""
        return host.lower() in _LOCALHOST_HOSTS
    except Exception:
        return False


def _http_post_embeddings(
    url: str,
    payload: dict[str, Any],
    *,
    timeout: int,
    api_key: str | None,
) -> list[Any]:
    """POST ``payload`` to ``url``, return the ``data[*].embedding`` rows."""

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        raise BrainEmbeddingEndpointUnavailable(
            f"embedding endpoint returned HTTP {exc.code}: {detail}"
        ) from exc
    except urllib.error.URLError as exc:  # type: ignore[attr-defined]
        raise BrainEmbeddingEndpointUnavailable(
            f"embedding endpoint unreachable at {url}: {exc.reason}"
        ) from exc
    except OSError as exc:
        raise BrainEmbeddingEndpointUnavailable(
            f"embedding endpoint I/O error at {url}: {exc}"
        ) from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BrainEmbeddingEndpointInvalid(
            f"embedding endpoint returned non-JSON response: {raw[:200]!r}"
        ) from exc

    if not isinstance(data, dict):
        raise BrainEmbeddingEndpointInvalid(
            "embedding endpoint response must be a JSON object"
        )
    items = data.get("data")
    if not isinstance(items, list):
        raise BrainEmbeddingEndpointInvalid(
            f"embedding endpoint response missing 'data' list; got keys: {list(data)}"
        )
    rows: list[Any] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise BrainEmbeddingEndpointInvalid(
                f"embedding endpoint data[{idx}] must be a JSON object"
            )
        embedding = item.get("embedding")
        if embedding is None:
            raise BrainEmbeddingEndpointInvalid(
                f"embedding endpoint data[{idx}] missing 'embedding' field"
            )
        rows.append(embedding)
    return rows


def _truncate_text(text: str, max_chars: int = 16000) -> str:
    """Truncate ``text`` to at most ``max_chars`` characters.

    Qwen3-Embedding-8B has an 8192-token context window.  For typical English /
    markdown text a ~4-chars-per-token average gives ~32 000 chars for the full
    window.  We use 16 000 chars (roughly 4 000 tokens) as a conservative ceiling
    that fits well inside the window while still capturing the leading, most
    semantically dense content of large memory-file chunks.  The trailing ellipsis
    signals truncation to the model.
    """

    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n…"


def _validate_texts(texts: Sequence[str]) -> tuple[str, ...]:
    if isinstance(texts, str):
        raise BrainEmbeddingEndpointInvalid(
            "texts must be a sequence of strings, not a single string"
        )
    try:
        values = tuple(texts)
    except TypeError as exc:
        raise BrainEmbeddingEndpointInvalid("texts must be a sequence of strings") from exc
    if not all(isinstance(t, str) for t in values):
        raise BrainEmbeddingEndpointInvalid("texts must contain only strings")
    return values


def _parse_rows(
    rows: list[Any],
    *,
    count: int,
    expected_dim: int,
) -> tuple[Vector, ...]:
    if len(rows) != count:
        raise BrainEmbeddingEndpointInvalid(
            f"embedding endpoint returned {len(rows)} vectors for {count} texts"
        )
    result: list[Vector] = []
    for idx, row in enumerate(rows):
        if not hasattr(row, "__iter__") or isinstance(row, (str, bytes)):
            raise BrainEmbeddingEndpointInvalid(
                f"embedding endpoint data[{idx}].embedding must be a numeric list"
            )
        floats: list[float] = []
        for component in row:
            try:
                v = float(component)
            except (TypeError, ValueError) as exc:
                raise BrainEmbeddingEndpointInvalid(
                    f"embedding endpoint data[{idx}] contains non-numeric component"
                ) from exc
            if not math.isfinite(v):
                raise BrainEmbeddingEndpointInvalid(
                    f"embedding endpoint data[{idx}] contains non-finite component"
                )
            floats.append(v)
        if len(floats) != expected_dim:
            raise BrainEmbeddingEndpointInvalid(
                f"embedding endpoint data[{idx}] has dim {len(floats)}; "
                f"adapter configured for dim {expected_dim}"
            )
        result.append(tuple(floats))
    return tuple(result)


__all__ = [
    "BrainEmbeddingEndpointError",
    "BrainEmbeddingEndpointInvalid",
    "BrainEmbeddingEndpointUnavailable",
    "DEFAULT_DIM",
    "DEFAULT_ENDPOINT",
    "DEFAULT_MODEL_ID",
    "DEFAULT_TIMEOUT_SECONDS",
    "OpenAIEndpointEmbeddingAdapter",
]
