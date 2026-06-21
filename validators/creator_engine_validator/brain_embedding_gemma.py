"""Local EmbeddingGemma adapter for brain recall.

The adapter keeps the validator package importable without optional ML
dependencies. Model loading is lazy, local-only, and can be replaced with an
injected model object for tests.
"""

from __future__ import annotations

import importlib
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from creator_engine_validator.brain_recall import Vector

DEFAULT_MODEL_ID = "google/embeddinggemma-300m"
DEFAULT_DIM = 768
KNOWN_OUTPUT_DIMS = frozenset({768, 512, 256, 128})


class BrainEmbeddingGemmaError(Exception):
    code = "CE-BRAIN-EMBEDDING-GEMMA-ERROR"


class BrainEmbeddingGemmaUnavailable(BrainEmbeddingGemmaError):
    code = "CE-BRAIN-EMBEDDING-GEMMA-UNAVAILABLE"


class BrainEmbeddingGemmaInvalid(BrainEmbeddingGemmaError):
    code = "CE-BRAIN-EMBEDDING-GEMMA-INVALID"


@dataclass
class EmbeddingGemmaAdapter:
    """EmbeddingAdapter implementation backed by a local EmbeddingGemma model."""

    model_path: str | Path | None = None
    cache_dir: str | Path | None = None
    output_dim: int = DEFAULT_DIM
    model_id: str = DEFAULT_MODEL_ID
    model: Any | None = None
    sentence_transformers_module: Any | None = None
    torch_module: Any | None = None
    requires_egress: bool = field(default=False, init=False)
    dim: int = field(init=False)
    device: str | None = field(default=None, init=False)
    _model: Any | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.output_dim not in KNOWN_OUTPUT_DIMS:
            allowed = ", ".join(str(dim) for dim in sorted(KNOWN_OUTPUT_DIMS, reverse=True))
            raise BrainEmbeddingGemmaInvalid(f"output_dim must be one of: {allowed}")
        if not isinstance(self.model_id, str) or not self.model_id.strip():
            raise BrainEmbeddingGemmaInvalid("model_id must be a non-empty string")
        self.model_id = self.model_id.strip()
        self.dim = self.output_dim
        self.requires_egress = False
        if self.model is not None:
            self._model = self.model

    def embed(self, texts: Sequence[str]) -> tuple[Vector, ...]:
        values = _validate_texts(texts)
        if not values:
            return ()
        model = self._ensure_model()
        raw_vectors = _encode_model(model, values)
        return _normalize_vectors(raw_vectors, count=len(values), dim=self.dim)

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model

        if self.model_path is None and self.cache_dir is None:
            raise BrainEmbeddingGemmaUnavailable(
                "EmbeddingGemmaAdapter requires a local model_path, cache_dir, or injected model; "
                "no network fallback is allowed."
            )

        model_path = Path(self.model_path).expanduser() if self.model_path is not None else None
        cache_dir = Path(self.cache_dir).expanduser() if self.cache_dir is not None else None
        if model_path is not None and not model_path.exists():
            raise BrainEmbeddingGemmaUnavailable(f"local EmbeddingGemma model_path does not exist: {model_path}")
        if cache_dir is not None and not cache_dir.exists():
            raise BrainEmbeddingGemmaUnavailable(f"local EmbeddingGemma cache_dir does not exist: {cache_dir}")

        st_module = self.sentence_transformers_module
        if st_module is None:
            try:
                st_module = importlib.import_module("sentence_transformers")
            except ImportError as exc:
                raise BrainEmbeddingGemmaUnavailable(
                    "sentence_transformers is not installed; install optional ML dependencies and provide "
                    "a local model_path/cache_dir. No model weights are downloaded implicitly."
                ) from exc

        sentence_transformer = getattr(st_module, "SentenceTransformer", None)
        if sentence_transformer is None:
            raise BrainEmbeddingGemmaUnavailable("sentence_transformers.SentenceTransformer is unavailable")

        self.device = select_best_device(self.torch_module)
        source = str(model_path) if model_path is not None else self.model_id
        kwargs: dict[str, Any] = {"device": self.device, "local_files_only": True}
        if cache_dir is not None:
            kwargs["cache_folder"] = str(cache_dir)

        try:
            self._model = sentence_transformer(source, **kwargs)
        except TypeError as exc:
            raise BrainEmbeddingGemmaUnavailable(
                "installed sentence_transformers does not support local_files_only; refusing to risk network fallback"
            ) from exc
        except Exception as exc:
            raise BrainEmbeddingGemmaUnavailable(f"failed to load local EmbeddingGemma model: {exc}") from exc

        return self._model


def select_best_device(torch_module: Any | None = None) -> str:
    """Return the best available local device without requiring torch."""

    torch = torch_module
    if torch is None:
        try:
            torch = importlib.import_module("torch")
        except ImportError:
            return "cpu"

    cuda = getattr(torch, "cuda", None)
    if _is_available(cuda):
        return "cuda"

    backends = getattr(torch, "backends", None)
    mps = getattr(backends, "mps", None) if backends is not None else None
    if _is_available(mps):
        return "mps"

    return "cpu"


def _is_available(candidate: Any) -> bool:
    is_available = getattr(candidate, "is_available", None)
    if is_available is None:
        return False
    try:
        return bool(is_available())
    except Exception:
        return False


def _validate_texts(texts: Sequence[str]) -> tuple[str, ...]:
    if isinstance(texts, str):
        raise BrainEmbeddingGemmaInvalid("texts must be a sequence of strings, not a single string")
    try:
        values = tuple(texts)
    except TypeError as exc:
        raise BrainEmbeddingGemmaInvalid("texts must be a sequence of strings") from exc
    if not all(isinstance(text, str) for text in values):
        raise BrainEmbeddingGemmaInvalid("texts must contain only strings")
    return values


def _encode_model(model: Any, texts: tuple[str, ...]) -> Any:
    encode = getattr(model, "encode", None)
    if encode is not None:
        try:
            return encode(list(texts), convert_to_numpy=False, normalize_embeddings=False)
        except TypeError:
            return encode(list(texts))
    if callable(model):
        return model(list(texts))
    raise BrainEmbeddingGemmaUnavailable("injected EmbeddingGemma model must provide encode(texts) or be callable")


def _normalize_vectors(raw_vectors: Any, *, count: int, dim: int) -> tuple[Vector, ...]:
    vectors = _as_vector_rows(raw_vectors)
    if len(vectors) != count:
        raise BrainEmbeddingGemmaInvalid(f"model returned {len(vectors)} vectors for {count} texts")

    normalized: list[Vector] = []
    for index, vector in enumerate(vectors):
        if len(vector) < dim:
            raise BrainEmbeddingGemmaInvalid(
                f"model returned vector {index} with dim {len(vector)}; expected at least {dim}"
            )
        trimmed = tuple(_float_component(value, index=index) for value in vector[:dim])
        if len(trimmed) != dim:
            raise BrainEmbeddingGemmaInvalid(f"model returned vector {index} with dim {len(trimmed)}; expected {dim}")
        normalized.append(trimmed)
    return tuple(normalized)


def _as_vector_rows(raw_vectors: Any) -> list[Sequence[Any]]:
    tolist = getattr(raw_vectors, "tolist", None)
    if tolist is not None:
        raw_vectors = tolist()
    if isinstance(raw_vectors, tuple):
        rows = list(raw_vectors)
    elif isinstance(raw_vectors, list):
        rows = raw_vectors
    else:
        try:
            rows = list(raw_vectors)
        except TypeError as exc:
            raise BrainEmbeddingGemmaInvalid("model returned a non-iterable embedding result") from exc
    return rows


def _float_component(value: Any, *, index: int) -> float:
    try:
        component = float(value)
    except (TypeError, ValueError) as exc:
        raise BrainEmbeddingGemmaInvalid(f"model returned non-numeric component in vector {index}") from exc
    if not math.isfinite(component):
        raise BrainEmbeddingGemmaInvalid(f"model returned non-finite component in vector {index}")
    return component


__all__ = [
    "BrainEmbeddingGemmaError",
    "BrainEmbeddingGemmaInvalid",
    "BrainEmbeddingGemmaUnavailable",
    "DEFAULT_DIM",
    "DEFAULT_MODEL_ID",
    "EmbeddingGemmaAdapter",
    "KNOWN_OUTPUT_DIMS",
    "select_best_device",
]
