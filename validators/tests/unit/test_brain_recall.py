from __future__ import annotations

import hashlib
import importlib.util
from dataclasses import asdict, is_dataclass
from typing import Any

import pytest

from creator_engine_validator.schema import validate_with_schema


SCHEMA = "schemas/brain-recall-record.schema.yaml"
AS_OF = "2026-06-21T00:00:00Z"
SOURCE_PATH = "docs/operations/PCL_PROTOCOL.md"
CHUNK_REF = "heading:recall-privacy"
PUBLIC_SCOPE = "public"
CONFIDENTIAL_SCOPE = "confidential"
CONTENT = "Markdown remains the source-of-truth; the vector store is derived."


def _content_hash(content: str = CONTENT) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _valid_entry(**overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "kind": "brain-recall-index-entry",
        "record_type": "brain_recall_index_entry",
        "schema_version": "1",
        "source_path": SOURCE_PATH,
        "chunk_ref": CHUNK_REF,
        "content_hash": _content_hash(),
        "as_of": AS_OF,
        "scope": PUBLIC_SCOPE,
        "requires_egress": False,
    }
    entry.update(overrides)
    return entry


def _entry_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    raise AssertionError(f"expected recall entry mapping/dataclass, got {type(value)!r}")


def _result_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "record"):
        return {"record": _entry_dict(value.record), "score": value.score}
    raise AssertionError(f"expected recall result mapping/dataclass, got {type(value)!r}")


def _recall_module():
    if importlib.util.find_spec("creator_engine_validator.brain_recall") is None:
        pytest.skip("Worker A runtime module creator_engine_validator.brain_recall is not present yet")
    from creator_engine_validator import brain_recall

    return brain_recall


class DeterministicFakeEmbedder:
    requires_egress = False
    model_id = "test-deterministic-fake"
    dim = 3

    def __init__(self) -> None:
        self.inputs: list[tuple[str, ...]] = []

    def embed(self, texts: list[str] | tuple[str, ...]) -> tuple[tuple[float, float, float], ...]:
        values = tuple(texts)
        self.inputs.append(values)
        vectors: list[tuple[float, float, float]] = []
        for text in values:
            encoded = text.encode("utf-8")
            vectors.append((float(len(encoded)), float(sum(encoded) % 997), float(encoded.count(b" "))))
        return tuple(vectors)


class EgressRequiringFakeEmbedder(DeterministicFakeEmbedder):
    requires_egress = True


def _record(recall: Any, *, content: str = CONTENT, scope: Any = PUBLIC_SCOPE, requires_egress: bool = False, chunk_ref: str = CHUNK_REF) -> Any:
    return recall.RecallRecord(
        source_path=SOURCE_PATH,
        chunk_ref=chunk_ref,
        content_hash=_content_hash(content),
        as_of=AS_OF,
        scope=scope,
        requires_egress=requires_egress,
    )


def _chunk(
    recall: Any,
    *,
    content: str = CONTENT,
    scope: Any = PUBLIC_SCOPE,
    requires_egress: bool = False,
    chunk_ref: str = CHUNK_REF,
) -> Any:
    return recall.RecallChunk(
        record=_record(recall, content=content, scope=scope, requires_egress=requires_egress, chunk_ref=chunk_ref),
        text=content,
    )


def test_recall_index_entry_schema_accepts_markdown_sot_pointer():
    assert validate_with_schema(
        _valid_entry(),
        SCHEMA,
        "brain-recall-entry.yaml",
        code="brain_recall_schema_violation",
        contract=SCHEMA,
    ) == []


def test_recall_index_entry_schema_rejects_non_markdown_source_path():
    errors = validate_with_schema(
        _valid_entry(source_path="https://example.invalid/source.md"),
        SCHEMA,
        "brain-recall-entry.yaml",
        code="brain_recall_schema_violation",
        contract=SCHEMA,
    )

    assert errors
    assert any(error.path == "brain-recall-entry.yaml:/source_path" for error in errors)


def test_recall_index_entry_schema_rejects_vector_payload_as_authority():
    errors = validate_with_schema(
        _valid_entry(embedding=[1, 2, 3]),
        SCHEMA,
        "brain-recall-entry.yaml",
        code="brain_recall_schema_violation",
        contract=SCHEMA,
    )

    assert errors
    assert any(error.path == "brain-recall-entry.yaml:/" for error in errors)


def test_adapter_rebuilds_and_queries_with_deterministic_fake_embedder_and_memory_store():
    recall = _recall_module()
    embedder = DeterministicFakeEmbedder()
    store = recall.InMemoryVectorStore()

    result = store.rebuild_from_source([_chunk(recall, requires_egress=True)], embedder)
    query_vector = embedder.embed((CONTENT,))[0]
    results = [_result_dict(hit) for hit in store.query(query_vector, top_k=1)]
    entry = store.records[0].to_dict()

    assert entry == _valid_entry()
    assert validate_with_schema(entry, SCHEMA, "entry", code="brain_recall_schema_violation", contract=SCHEMA) == []
    assert result.to_dict() == {"count": 1, "model_id": "test-deterministic-fake", "dim": 3}
    assert len(store.records) == 1
    assert embedder.inputs == [(CONTENT,), (CONTENT,)]
    assert results[0]["record"] == entry


def test_privacy_gate_refuses_confidential_scope_with_egress_embedder_without_consent():
    recall = _recall_module()
    store = recall.InMemoryVectorStore()

    with pytest.raises(recall.BrainRecallPrivacyRefused):
        store.rebuild_from_source(
            [_chunk(recall, scope=CONFIDENTIAL_SCOPE, requires_egress=False)],
            EgressRequiringFakeEmbedder(),
            allow_confidential_egress=False,
        )

    assert store.records == ()


def test_rebuild_derives_stored_egress_from_embedder_not_input_record():
    recall = _recall_module()
    embedder = EgressRequiringFakeEmbedder()
    store = recall.InMemoryVectorStore()

    store.rebuild_from_source([_chunk(recall, requires_egress=False)], embedder)
    query_vector = embedder.embed((CONTENT,))[0]
    results = [_result_dict(hit) for hit in store.query(query_vector, top_k=1)]
    entry = store.records[0].to_dict()

    assert entry == _valid_entry(requires_egress=True)
    assert results[0]["record"] == entry


def test_privacy_gate_allows_confidential_scope_with_explicit_consent_and_marks_egress():
    recall = _recall_module()
    store = recall.InMemoryVectorStore()

    result = store.rebuild_from_source(
        [_chunk(recall, scope=CONFIDENTIAL_SCOPE, requires_egress=False)],
        EgressRequiringFakeEmbedder(),
        allow_confidential_egress=True,
    )
    entry = store.records[0].to_dict()

    assert entry == _valid_entry(scope=CONFIDENTIAL_SCOPE, requires_egress=True)
    assert result.count == 1
    assert validate_with_schema(entry, SCHEMA, "entry", code="brain_recall_schema_violation", contract=SCHEMA) == []


def test_adapter_rebuild_is_deterministic_for_same_chunk_input():
    recall = _recall_module()
    first = recall.InMemoryVectorStore()
    second = recall.InMemoryVectorStore()
    chunks = (
        _chunk(recall, chunk_ref="heading:z"),
        _chunk(recall, chunk_ref="heading:a"),
    )

    first_result = first.rebuild_from_source(chunks, DeterministicFakeEmbedder())
    second_result = second.rebuild_from_source(reversed(chunks), DeterministicFakeEmbedder())

    assert first_result.to_dict() == second_result.to_dict()
    assert [entry.to_dict() for entry in first.records] == [entry.to_dict() for entry in second.records]
    assert [entry.record.to_dict() for entry in first.entries] == [entry.record.to_dict() for entry in second.entries]
    assert [entry.vector for entry in first.entries] == [entry.vector for entry in second.entries]
