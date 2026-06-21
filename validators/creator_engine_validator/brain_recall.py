"""Company-brain recall adapter spine.

This module is intentionally local and dependency-free: it defines adapter
protocols, deterministic offline implementations, and the privacy gate needed
before any egress-capable embedder sees recall chunks.
"""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import math
import os
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

Vector = tuple[float, ...]
Scope = str | Mapping[str, Any]

RECALL_ENTRY_KIND = "brain-recall-index-entry"
RECALL_RECORD_TYPE = "brain_recall_index_entry"
RECALL_SCHEMA_VERSION = "1"

_CONFIDENTIAL_SCOPE_VALUES = {"confidential", "ce-ops"}
_CONFIDENTIAL_SCOPE_FIELDS = {"confidentiality", "sensitivity", "scope"}


class BrainRecallError(Exception):
    code = "CE-BRAIN-RECALL-ERROR"


class BrainRecallInvalid(BrainRecallError):
    code = "CE-BRAIN-RECALL-INVALID"


class BrainRecallPrivacyRefused(BrainRecallError):
    code = "CE-BRAIN-RECALL-PRIVACY-REFUSED"


BrainRecallRefused = BrainRecallPrivacyRefused
RecallPrivacyRefused = BrainRecallPrivacyRefused


class EmbeddingAdapter(Protocol):
    requires_egress: bool
    model_id: str
    dim: int

    def embed(self, texts: Sequence[str]) -> tuple[Vector, ...]:
        """Embed texts in order and return one vector per text."""


class VectorStoreAdapter(Protocol):
    def upsert(
        self,
        entries: Iterable[RecallVector] | RecallVector | RecallRecord,
        vector: Sequence[float] | None = None,
    ) -> int:
        """Insert or replace vectors by recall key."""

    def query(self, vector: Sequence[float], top_k: int = 5) -> tuple[RecallHit, ...]:
        """Return the top-K nearest records for the query vector."""

    def rebuild_from_source(
        self,
        chunks: Iterable[RecallChunk],
        embedder: EmbeddingAdapter,
        *,
        allow_confidential_egress: bool = False,
    ) -> RebuildResult:
        """Replace the store with vectors derived from source chunks."""

    def delete(self, keys: Iterable[RecallKey | RecallRecord | tuple[str, str]]) -> int:
        """Delete vectors by recall key."""


@dataclass(frozen=True, order=True)
class RecallKey:
    source_path: str
    chunk_ref: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path", _nonempty_text("source_path", self.source_path))
        object.__setattr__(self, "chunk_ref", _nonempty_text("chunk_ref", self.chunk_ref))

    def to_dict(self) -> dict[str, str]:
        return {"source_path": self.source_path, "chunk_ref": self.chunk_ref}


@dataclass(frozen=True)
class RecallRecord:
    kind: str = field(default=RECALL_ENTRY_KIND, init=False)
    record_type: str = field(default=RECALL_RECORD_TYPE, init=False)
    schema_version: str = field(default=RECALL_SCHEMA_VERSION, init=False)
    source_path: str
    chunk_ref: str
    content_hash: str
    as_of: str
    scope: Scope
    requires_egress: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path", _nonempty_text("source_path", self.source_path))
        object.__setattr__(self, "chunk_ref", _nonempty_text("chunk_ref", self.chunk_ref))
        object.__setattr__(self, "content_hash", _nonempty_text("content_hash", self.content_hash))
        object.__setattr__(self, "as_of", _nonempty_text("as_of", self.as_of))
        object.__setattr__(self, "scope", _normalize_scope(self.scope))
        object.__setattr__(self, "requires_egress", bool(self.requires_egress))

    @property
    def key(self) -> RecallKey:
        return RecallKey(self.source_path, self.chunk_ref)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "record_type": self.record_type,
            "schema_version": self.schema_version,
            "source_path": self.source_path,
            "chunk_ref": self.chunk_ref,
            "content_hash": self.content_hash,
            "as_of": self.as_of,
            "scope": _stable_copy(self.scope),
            "requires_egress": self.requires_egress,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> RecallRecord:
        return cls(
            source_path=data.get("source_path"),
            chunk_ref=data.get("chunk_ref"),
            content_hash=data.get("content_hash"),
            as_of=data.get("as_of"),
            scope=data.get("scope"),
            requires_egress=bool(data.get("requires_egress", False)),
        )


@dataclass(frozen=True)
class RecallChunk:
    record: RecallRecord
    text: str

    def __post_init__(self) -> None:
        record = self.record
        if isinstance(record, Mapping):
            record = RecallRecord.from_mapping(record)
        if not isinstance(record, RecallRecord):
            raise BrainRecallInvalid("record must be a RecallRecord or mapping")
        if not isinstance(self.text, str):
            raise BrainRecallInvalid("text must be a string")
        object.__setattr__(self, "record", record)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> RecallChunk:
        text = data.get("text")
        raw_record = data.get("record")
        record = (
            RecallRecord.from_mapping(raw_record)
            if isinstance(raw_record, Mapping)
            else RecallRecord.from_mapping(data)
        )
        return cls(record=record, text=text)


@dataclass(frozen=True)
class RecallVector:
    record: RecallRecord
    vector: Vector

    def __post_init__(self) -> None:
        record = self.record
        if isinstance(record, Mapping):
            record = RecallRecord.from_mapping(record)
        if not isinstance(record, RecallRecord):
            raise BrainRecallInvalid("record must be a RecallRecord or mapping")
        object.__setattr__(self, "record", record)
        object.__setattr__(self, "vector", _normalize_vector(self.vector))


@dataclass(frozen=True)
class RecallHit:
    record: RecallRecord
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {"record": self.record.to_dict(), "score": self.score}


@dataclass(frozen=True)
class RebuildResult:
    count: int
    model_id: str
    dim: int

    def to_dict(self) -> dict[str, Any]:
        return {"count": self.count, "model_id": self.model_id, "dim": self.dim}


@dataclass(frozen=True)
class DeterministicFakeEmbedding:
    dim: int = 32
    model_id: str = "ce-deterministic-fake-embedding-v1"
    requires_egress: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.dim, int) or self.dim <= 0:
            raise BrainRecallInvalid("dim must be a positive integer")
        object.__setattr__(self, "model_id", _nonempty_text("model_id", self.model_id))
        object.__setattr__(self, "requires_egress", bool(self.requires_egress))

    def embed(self, texts: Sequence[str]) -> tuple[Vector, ...]:
        if isinstance(texts, str):
            raise BrainRecallInvalid("texts must be a sequence of strings, not a single string")
        vectors: list[Vector] = []
        for text in texts:
            if not isinstance(text, str):
                raise BrainRecallInvalid("texts must contain only strings")
            vectors.append(tuple(_fake_component(self.model_id, text, idx) for idx in range(self.dim)))
        return tuple(vectors)


DeterministicFakeEmbeddingAdapter = DeterministicFakeEmbedding
FakeEmbeddingAdapter = DeterministicFakeEmbedding


@dataclass(frozen=True)
class BrainRecallAdapter:
    embedder: Any
    store: Any

    def index_chunk(
        self,
        *,
        source_path: str,
        chunk_ref: str,
        content: str,
        as_of: str,
        scope: Scope,
        explicit_consent: bool = False,
    ) -> RecallRecord:
        if not isinstance(content, str):
            raise BrainRecallInvalid("content must be a string")
        record = RecallRecord(
            source_path=source_path,
            chunk_ref=chunk_ref,
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            as_of=as_of,
            scope=scope,
            requires_egress=bool(getattr(self.embedder, "requires_egress", False)),
        )
        require_embedding_allowed(
            (RecallChunk(record=record, text=content),),
            self.embedder,
            allow_confidential_egress=explicit_consent,
        )
        _store_upsert(self.store, record, _embed_one(self.embedder, content))
        return record

    def query(
        self,
        content: str,
        *,
        scope: str | None = None,
        as_of: str | None = None,
        limit: int = 10,
    ) -> tuple[Any, ...]:
        if limit <= 0:
            return ()
        if not isinstance(content, str):
            raise BrainRecallInvalid("content must be a string")
        vector = _embed_one(self.embedder, content)
        search = getattr(self.store, "search", None)
        if callable(search):
            return tuple(search(vector, scope=scope, as_of=as_of, limit=limit))
        query = getattr(self.store, "query", None)
        if not callable(query):
            raise BrainRecallInvalid("store must provide search(...) or query(...)")
        hits = query(vector, top_k=limit)
        filtered: list[dict[str, Any]] = []
        for hit in hits:
            record = getattr(hit, "record", None)
            if not isinstance(record, RecallRecord):
                filtered.append(copy.deepcopy(hit))
                continue
            if scope is not None and record.scope != scope:
                continue
            if as_of is not None and record.as_of > as_of:
                continue
            filtered.append({"entry": record.to_dict(), "score": getattr(hit, "score", 0.0)})
            if len(filtered) >= limit:
                break
        return tuple(filtered)


@dataclass
class InMemoryVectorStore:
    dim: int | None = None
    _entries: dict[RecallKey, RecallVector] = field(default_factory=dict, init=False, repr=False)

    def __init__(self, entries: Iterable[RecallVector] = (), *, dim: int | None = None) -> None:
        if dim is not None and (not isinstance(dim, int) or dim <= 0):
            raise BrainRecallInvalid("dim must be a positive integer when provided")
        self.dim = dim
        self._entries = {}
        self.upsert(entries)

    def upsert(
        self,
        entries: Iterable[RecallVector] | RecallVector | RecallRecord | Mapping[str, Any],
        vector: Sequence[float] | None = None,
    ) -> int:
        count = 0
        if vector is not None:
            raw_entries: Iterable[Any] = (RecallVector(record=entries, vector=vector),)
        elif isinstance(entries, (RecallVector, Mapping)):
            raw_entries = (entries,)
        else:
            raw_entries = entries
        for raw_entry in raw_entries:
            entry = _normalize_recall_vector(raw_entry)
            self._require_dim(len(entry.vector))
            self._entries[entry.record.key] = entry
            count += 1
        return count

    def query(self, vector: Sequence[float], top_k: int = 5) -> tuple[RecallHit, ...]:
        if top_k <= 0 or not self._entries:
            return ()
        query_vector = _normalize_vector(vector)
        self._require_dim(len(query_vector))
        hits = [
            RecallHit(record=entry.record, score=_cosine(query_vector, entry.vector))
            for entry in self._entries.values()
        ]
        return tuple(
            sorted(
                hits,
                key=lambda hit: (
                    -hit.score,
                    hit.record.source_path,
                    hit.record.chunk_ref,
                    hit.record.content_hash,
                    hit.record.as_of,
                ),
            )[:top_k]
        )

    def rebuild_from_source(
        self,
        chunks: Iterable[RecallChunk],
        embedder: EmbeddingAdapter,
        *,
        allow_confidential_egress: bool = False,
    ) -> RebuildResult:
        source_chunks = tuple(sorted((_normalize_chunk(chunk) for chunk in chunks), key=lambda c: c.record.key))
        require_embedding_allowed(
            source_chunks,
            embedder,
            allow_confidential_egress=allow_confidential_egress,
        )
        vectors = tuple(_normalize_vector(vector) for vector in embedder.embed(tuple(chunk.text for chunk in source_chunks)))
        if len(vectors) != len(source_chunks):
            raise BrainRecallInvalid("embedder returned a different vector count than input text count")
        if any(len(vector) != embedder.dim for vector in vectors):
            raise BrainRecallInvalid("embedder returned a vector with a dimension different from embedder.dim")
        self._entries = {}
        self.dim = embedder.dim
        requires_egress = bool(getattr(embedder, "requires_egress", False))
        self.upsert(
            RecallVector(record=_record_with_egress(chunk.record, requires_egress), vector=vector)
            for chunk, vector in zip(source_chunks, vectors, strict=True)
        )
        return RebuildResult(count=len(source_chunks), model_id=embedder.model_id, dim=embedder.dim)

    def delete(self, keys: Iterable[RecallKey | RecallRecord | tuple[str, str]]) -> int:
        count = 0
        for raw_key in keys:
            key = _normalize_key(raw_key)
            if key in self._entries:
                del self._entries[key]
                count += 1
        if not self._entries:
            self.dim = None
        return count

    @property
    def entries(self) -> tuple[RecallVector, ...]:
        return tuple(self._entries[key] for key in sorted(self._entries))

    @property
    def records(self) -> tuple[RecallRecord, ...]:
        return tuple(entry.record for entry in self.entries)

    def _require_dim(self, dim: int) -> None:
        if self.dim is None:
            self.dim = dim
            return
        if self.dim != dim:
            raise BrainRecallInvalid("vector dimension does not match the store dimension")


InMemoryVectorStoreAdapter = InMemoryVectorStore


def require_embedding_allowed(
    chunks: Iterable[RecallChunk],
    embedder: EmbeddingAdapter,
    *,
    allow_confidential_egress: bool = False,
) -> None:
    if not bool(getattr(embedder, "requires_egress", False)):
        return
    if allow_confidential_egress is True:
        return
    confidential = sorted(
        (chunk.record for chunk in (_normalize_chunk(chunk) for chunk in chunks) if is_confidential_scope(chunk.record.scope)),
        key=lambda record: record.key,
    )
    if confidential:
        record = confidential[0]
        raise BrainRecallPrivacyRefused(
            "confidential recall chunk requires explicit consent before egress embedding: "
            f"{record.source_path}#{record.chunk_ref}"
        )


def _store_upsert(store: Any, record: RecallRecord, vector: Vector) -> None:
    upsert = getattr(store, "upsert", None)
    if not callable(upsert):
        raise BrainRecallInvalid("store must provide upsert(...)")
    try:
        upsert(record, vector)
    except TypeError as direct_exc:
        try:
            upsert((RecallVector(record=record, vector=vector),))
        except TypeError:
            raise direct_exc


def _embed_one(embedder: Any, text: str) -> Vector:
    embed = getattr(embedder, "embed", None)
    if not callable(embed):
        raise BrainRecallInvalid("embedder must provide embed(...)")
    if _embed_prefers_single_text(embed):
        return _normalize_embedding_output(embed(text))
    try:
        return _normalize_embedding_output(embed((text,)))
    except (AttributeError, TypeError, BrainRecallInvalid):
        return _normalize_embedding_output(embed(text))


def _embed_prefers_single_text(embed: Any) -> bool:
    try:
        parameters = list(inspect.signature(embed).parameters.values())
    except (TypeError, ValueError):
        return False
    if not parameters:
        return False
    first = parameters[0]
    name = first.name.lower()
    if name in {"text", "content", "chunk"}:
        return True
    if name in {"texts", "contents", "chunks"}:
        return False
    annotation = first.annotation
    return annotation is str or annotation == "str"


def _normalize_embedding_output(value: Any) -> Vector:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) == 1:
        first = value[0]
        if not _is_numeric_scalar(first):
            return _normalize_vector(first)
    return _normalize_vector(value)


def is_confidential_scope(scope: Any) -> bool:
    if isinstance(scope, str):
        return _is_confidential_value(scope)
    if isinstance(scope, Mapping):
        for key, value in scope.items():
            normalized_key = _scope_token(str(key)).replace("-", "_")
            if normalized_key in _CONFIDENTIAL_SCOPE_FIELDS and _contains_confidential_marker(value):
                return True
    return False


def _stable_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise BrainRecallInvalid("recall values must be JSON-compatible") from exc


def _stable_copy(value: Any) -> Any:
    return json.loads(_stable_json(value))


def _nonempty_text(name: str, value: Any) -> str:
    if isinstance(value, os.PathLike):
        value = os.fspath(value)
    if not isinstance(value, str) or not value:
        raise BrainRecallInvalid(f"{name} must be a non-empty string")
    return value


def _normalize_scope(scope: Any) -> str | dict[str, Any]:
    if isinstance(scope, str) and scope:
        return scope
    if isinstance(scope, Mapping) and scope:
        copied = _stable_copy(dict(scope))
        if not isinstance(copied, dict) or not copied:
            raise BrainRecallInvalid("scope must be a non-empty string or mapping")
        return copied
    raise BrainRecallInvalid("scope must be a non-empty string or mapping")


def _normalize_vector(vector: Sequence[float]) -> Vector:
    if isinstance(vector, (str, bytes)):
        raise BrainRecallInvalid("vector must be a non-empty numeric sequence")
    values: list[float] = []
    try:
        iterator = iter(vector)
    except TypeError as exc:
        raise BrainRecallInvalid("vector must be a non-empty numeric sequence") from exc
    for raw in iterator:
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise BrainRecallInvalid("vector must contain only numeric values") from exc
        if not math.isfinite(value):
            raise BrainRecallInvalid("vector must contain only finite numeric values")
        values.append(value)
    if not values:
        raise BrainRecallInvalid("vector must be a non-empty numeric sequence")
    return tuple(values)


def _normalize_recall_vector(value: Any) -> RecallVector:
    if isinstance(value, RecallVector):
        return value
    if isinstance(value, Mapping):
        if "record" in value and "vector" in value:
            return RecallVector(record=value["record"], vector=value["vector"])
        if "entry" in value and "vector" in value:
            return RecallVector(record=value["entry"], vector=value["vector"])
    raise BrainRecallInvalid("upsert entries must be RecallVector values or mappings with record/vector")


def _record_with_egress(record: RecallRecord, requires_egress: bool) -> RecallRecord:
    if record.requires_egress == bool(requires_egress):
        return record
    return RecallRecord(
        source_path=record.source_path,
        chunk_ref=record.chunk_ref,
        content_hash=record.content_hash,
        as_of=record.as_of,
        scope=record.scope,
        requires_egress=requires_egress,
    )


def _normalize_key(key: RecallKey | RecallRecord | tuple[str, str]) -> RecallKey:
    if isinstance(key, RecallKey):
        return key
    if isinstance(key, RecallRecord):
        return key.key
    if isinstance(key, tuple) and len(key) == 2:
        return RecallKey(source_path=key[0], chunk_ref=key[1])
    raise BrainRecallInvalid("delete keys must be RecallKey, RecallRecord, or (source_path, chunk_ref)")


def _normalize_chunk(chunk: RecallChunk | Mapping[str, Any]) -> RecallChunk:
    if isinstance(chunk, RecallChunk):
        return chunk
    if isinstance(chunk, Mapping):
        return RecallChunk.from_mapping(chunk)
    raise BrainRecallInvalid("chunks must be RecallChunk values or mappings")


def _fake_component(model_id: str, text: str, index: int) -> float:
    material = f"{model_id}\0{text}\0{index}".encode("utf-8")
    raw = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    value = (raw / ((1 << 64) - 1)) * 2.0 - 1.0
    return round(value, 12)


def _cosine(left: Vector, right: Vector) -> float:
    if len(left) != len(right):
        raise BrainRecallInvalid("query vector dimension does not match stored vector dimension")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    score = sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)
    return 0.0 if abs(score) < 1e-15 else score


def _scope_token(value: str) -> str:
    return re.sub(r"\s+", "-", value.strip().lower().replace("_", "-"))


def _is_confidential_value(value: str) -> bool:
    return _scope_token(value) in _CONFIDENTIAL_SCOPE_VALUES


def _contains_confidential_marker(value: Any) -> bool:
    if isinstance(value, str):
        return _is_confidential_value(value)
    if isinstance(value, bool):
        return value
    if isinstance(value, Mapping):
        return any(_contains_confidential_marker(child) for child in value.values())
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_contains_confidential_marker(child) for child in value)
    return False


def _is_numeric_scalar(value: Any) -> bool:
    if isinstance(value, (str, bytes)):
        return False
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


__all__ = [
    "BrainRecallAdapter",
    "BrainRecallError",
    "BrainRecallInvalid",
    "BrainRecallPrivacyRefused",
    "BrainRecallRefused",
    "DeterministicFakeEmbedding",
    "DeterministicFakeEmbeddingAdapter",
    "EmbeddingAdapter",
    "FakeEmbeddingAdapter",
    "InMemoryVectorStore",
    "InMemoryVectorStoreAdapter",
    "RECALL_ENTRY_KIND",
    "RECALL_RECORD_TYPE",
    "RECALL_SCHEMA_VERSION",
    "RecallChunk",
    "RecallHit",
    "RecallKey",
    "RecallPrivacyRefused",
    "RecallRecord",
    "RecallVector",
    "RebuildResult",
    "Vector",
    "VectorStoreAdapter",
    "is_confidential_scope",
    "require_embedding_allowed",
]
