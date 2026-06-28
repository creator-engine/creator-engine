"""Unit tests for the OpenAI-compatible HTTP endpoint embedder adapter.

All tests mock the HTTP layer — no live network call is made.  The standard
urllib.request path is replaced with a captured-call stub so CI runs offline.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from creator_engine_validator.brain_embedding_openai_endpoint import (
    BrainEmbeddingEndpointInvalid,
    BrainEmbeddingEndpointUnavailable,
    DEFAULT_DIM,
    DEFAULT_ENDPOINT,
    DEFAULT_MODEL_ID,
    OpenAIEndpointEmbeddingAdapter,
    _is_localhost_endpoint,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(embeddings: list[list[float]]) -> dict[str, Any]:
    """Build a minimal OpenAI-compatible /v1/embeddings response body."""
    return {
        "object": "list",
        "data": [
            {"object": "embedding", "embedding": vec, "index": idx}
            for idx, vec in enumerate(embeddings)
        ],
        "model": DEFAULT_MODEL_ID,
        "usage": {"prompt_tokens": 4, "total_tokens": 4},
    }


def _stub_getter(embeddings: list[list[float]]):
    """Return a getter callable that echoes back fixed embeddings."""
    captured: list[tuple[str, dict]] = []

    def getter(url: str, payload: dict) -> list[list[float]]:
        captured.append((url, payload))
        return [list(e) for e in embeddings]

    getter.captured = captured  # type: ignore[attr-defined]
    return getter


def _dim_vec(dim: int, seed: float = 0.1) -> list[float]:
    return [seed + i * 0.001 for i in range(dim)]


# ---------------------------------------------------------------------------
# Construction and attribute defaults
# ---------------------------------------------------------------------------


def test_defaults_point_to_localhost_vllm():
    adapter = OpenAIEndpointEmbeddingAdapter()

    assert adapter.endpoint == DEFAULT_ENDPOINT
    assert adapter.model_id == DEFAULT_MODEL_ID
    assert adapter.dim == DEFAULT_DIM
    # Localhost endpoint must NOT require egress.
    assert adapter.requires_egress is False


def test_localhost_variants_do_not_require_egress():
    for url in (
        "http://127.0.0.1:8989/v1/embeddings",
        "http://[::1]:8989/v1/embeddings",
        "http://localhost:8989/v1/embeddings",
    ):
        adapter = OpenAIEndpointEmbeddingAdapter(endpoint=url)
        assert adapter.requires_egress is False, f"expected no egress for {url}"


def test_remote_endpoint_sets_requires_egress_true():
    adapter = OpenAIEndpointEmbeddingAdapter(
        endpoint="https://api.openai.com/v1/embeddings",
        model_id="text-embedding-3-small",
        dim=1536,
    )
    assert adapter.requires_egress is True


def test_rejects_empty_endpoint():
    with pytest.raises(BrainEmbeddingEndpointInvalid, match="endpoint"):
        OpenAIEndpointEmbeddingAdapter(endpoint="")


def test_rejects_empty_model_id():
    with pytest.raises(BrainEmbeddingEndpointInvalid, match="model_id"):
        OpenAIEndpointEmbeddingAdapter(model_id="")


def test_rejects_non_positive_dim():
    with pytest.raises(BrainEmbeddingEndpointInvalid, match="dim"):
        OpenAIEndpointEmbeddingAdapter(dim=0)


def test_rejects_non_positive_timeout():
    with pytest.raises(BrainEmbeddingEndpointInvalid, match="timeout"):
        OpenAIEndpointEmbeddingAdapter(timeout=0)


# ---------------------------------------------------------------------------
# embed() — happy path via injected HTTP getter
# ---------------------------------------------------------------------------


def test_embed_single_text_returns_one_vector():
    dim = 4096
    vec = _dim_vec(dim)
    getter = _stub_getter([vec])
    adapter = OpenAIEndpointEmbeddingAdapter(dim=dim).with_http_getter(getter)

    result = adapter.embed(("hello world",))

    assert len(result) == 1
    assert len(result[0]) == dim
    assert result[0][0] == pytest.approx(vec[0])
    # Verify payload sent to endpoint contains model and input.
    _, payload = getter.captured[0]
    assert payload["model"] == DEFAULT_MODEL_ID
    assert payload["input"] == ["hello world"]


def test_embed_batch_returns_one_vector_per_text():
    dim = 4096
    texts = ("alpha", "beta", "gamma")
    vecs = [_dim_vec(dim, seed=float(i) * 0.01) for i in range(len(texts))]
    getter = _stub_getter(vecs)
    adapter = OpenAIEndpointEmbeddingAdapter(dim=dim).with_http_getter(getter)

    result = adapter.embed(texts)

    assert len(result) == 3
    for i, vec in enumerate(result):
        assert len(vec) == dim
        assert vec[0] == pytest.approx(vecs[i][0])


def test_embed_empty_sequence_returns_empty_tuple():
    adapter = OpenAIEndpointEmbeddingAdapter()
    result = adapter.embed(())
    assert result == ()


def test_embed_list_of_texts_also_accepted():
    dim = 4096
    getter = _stub_getter([_dim_vec(dim)])
    adapter = OpenAIEndpointEmbeddingAdapter(dim=dim).with_http_getter(getter)

    result = adapter.embed(["single"])
    assert len(result) == 1


# ---------------------------------------------------------------------------
# embed() — validation errors
# ---------------------------------------------------------------------------


def test_embed_rejects_bare_string():
    adapter = OpenAIEndpointEmbeddingAdapter()
    with pytest.raises(BrainEmbeddingEndpointInvalid, match="sequence of strings"):
        adapter.embed("not a sequence")


def test_embed_rejects_sequence_with_non_string():
    getter = _stub_getter([[0.1] * DEFAULT_DIM])
    adapter = OpenAIEndpointEmbeddingAdapter().with_http_getter(getter)
    with pytest.raises(BrainEmbeddingEndpointInvalid, match="strings"):
        adapter.embed([42])  # type: ignore[list-item]


def test_embed_raises_when_server_returns_wrong_vector_count():
    # Server returns 2 vectors for 1 input (mismatch).
    dim = 4096
    getter = _stub_getter([_dim_vec(dim), _dim_vec(dim)])
    adapter = OpenAIEndpointEmbeddingAdapter(dim=dim).with_http_getter(getter)

    with pytest.raises(BrainEmbeddingEndpointInvalid, match="1 texts"):
        adapter.embed(("one",))


def test_embed_raises_when_server_returns_wrong_dimension():
    dim = 4096
    wrong_dim_vec = [0.1] * (dim // 2)  # half the expected dim
    getter = _stub_getter([wrong_dim_vec])
    adapter = OpenAIEndpointEmbeddingAdapter(dim=dim).with_http_getter(getter)

    with pytest.raises(BrainEmbeddingEndpointInvalid, match="dim"):
        adapter.embed(("hello",))


# ---------------------------------------------------------------------------
# HTTP layer error handling (simulated via urllib errors)
# ---------------------------------------------------------------------------


def test_http_error_raises_unavailable(monkeypatch):
    import urllib.error
    import urllib.request

    def mock_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(
            url="http://127.0.0.1:8989/v1/embeddings",
            code=503,
            msg="Service Unavailable",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        )

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    adapter = OpenAIEndpointEmbeddingAdapter()
    with pytest.raises(BrainEmbeddingEndpointUnavailable, match="HTTP 503"):
        adapter.embed(("test",))


def test_url_error_raises_unavailable(monkeypatch):
    import urllib.error
    import urllib.request

    def mock_urlopen(req, timeout=None):
        raise urllib.error.URLError(reason="Connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    adapter = OpenAIEndpointEmbeddingAdapter()
    with pytest.raises(BrainEmbeddingEndpointUnavailable, match="unreachable"):
        adapter.embed(("test",))


def test_non_json_response_raises_invalid(monkeypatch):
    import io
    import urllib.request

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return b"not json"

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: FakeResponse())
    adapter = OpenAIEndpointEmbeddingAdapter()
    with pytest.raises(BrainEmbeddingEndpointInvalid, match="non-JSON"):
        adapter.embed(("test",))


def test_missing_data_field_raises_invalid(monkeypatch):
    import urllib.request

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return json.dumps({"object": "list"}).encode("utf-8")

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: FakeResponse())
    adapter = OpenAIEndpointEmbeddingAdapter()
    with pytest.raises(BrainEmbeddingEndpointInvalid, match="'data' list"):
        adapter.embed(("test",))


# ---------------------------------------------------------------------------
# _is_localhost_endpoint helper
# ---------------------------------------------------------------------------


def test_is_localhost_endpoint_identifies_loopback_addresses():
    assert _is_localhost_endpoint("http://127.0.0.1:8989/v1/embeddings") is True
    assert _is_localhost_endpoint("http://localhost/v1/embeddings") is True
    assert _is_localhost_endpoint("http://[::1]:8989/v1/embeddings") is True
    assert _is_localhost_endpoint("https://api.openai.com/v1/embeddings") is False
    assert _is_localhost_endpoint("https://example.com") is False


# ---------------------------------------------------------------------------
# Protocol compliance (EmbeddingAdapter shape)
# ---------------------------------------------------------------------------


def test_adapter_satisfies_embedding_adapter_protocol():
    """OpenAIEndpointEmbeddingAdapter must carry requires_egress, model_id, dim, and embed()."""

    adapter = OpenAIEndpointEmbeddingAdapter()
    assert hasattr(adapter, "requires_egress")
    assert hasattr(adapter, "model_id")
    assert hasattr(adapter, "dim")
    assert callable(getattr(adapter, "embed", None))


def test_make_embedder_vllm_openai_returns_endpoint_adapter():
    """brain_ingest_runtime.make_embedder('vllm-openai') must return the endpoint adapter."""

    from creator_engine_validator.brain_ingest_runtime import make_embedder
    from creator_engine_validator.brain_embedding_openai_endpoint import (
        OpenAIEndpointEmbeddingAdapter,
    )

    adapter = make_embedder("vllm-openai")
    assert isinstance(adapter, OpenAIEndpointEmbeddingAdapter)
    assert adapter.endpoint == DEFAULT_ENDPOINT
    assert adapter.dim == DEFAULT_DIM


def test_make_embedder_openai_endpoint_alias_also_works():
    from creator_engine_validator.brain_ingest_runtime import make_embedder
    from creator_engine_validator.brain_embedding_openai_endpoint import (
        OpenAIEndpointEmbeddingAdapter,
    )

    adapter = make_embedder("openai-endpoint")
    assert isinstance(adapter, OpenAIEndpointEmbeddingAdapter)


def test_make_embedder_passes_endpoint_overrides():
    from creator_engine_validator.brain_ingest_runtime import make_embedder

    adapter = make_embedder(
        "vllm-openai",
        endpoint="http://127.0.0.1:9999/v1/embeddings",
        endpoint_model_id="my-model",
        endpoint_dim=768,
    )
    assert adapter.endpoint == "http://127.0.0.1:9999/v1/embeddings"
    assert adapter.model_id == "my-model"
    assert adapter.dim == 768
