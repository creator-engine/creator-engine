from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from creator_engine_validator import brain_recall
from creator_engine_validator.brain_sqlite_vec import SqliteVecStore, default_recall_db_path


AS_OF = "2026-06-21T00:00:00Z"
SOURCE_PATH = "docs/operations/PCL_PROTOCOL.md"
PUBLIC_SCOPE = "public"
CONFIDENTIAL_SCOPE = "confidential"
CONTENT = "Markdown remains the source-of-truth; the vector store is derived."


class DeterministicFakeEmbedder:
    requires_egress = False
    model_id = "test-deterministic-fake"
    dim = 3

    def __init__(self) -> None:
        self.inputs: list[tuple[str, ...]] = []

    def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, float, float], ...]:
        self.inputs.append(tuple(texts))
        vectors: list[tuple[float, float, float]] = []
        for text in texts:
            encoded = text.encode("utf-8")
            vectors.append((float(len(encoded)), float(sum(encoded) % 997), float(encoded.count(b" "))))
        return tuple(vectors)


class EgressRequiringFakeEmbedder(DeterministicFakeEmbedder):
    requires_egress = True


def _content_hash(content: str = CONTENT) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _record(
    *,
    source_path: str = SOURCE_PATH,
    chunk_ref: str = "heading:recall-privacy",
    content: str = CONTENT,
    scope: Any = PUBLIC_SCOPE,
    requires_egress: bool = False,
) -> brain_recall.RecallRecord:
    return brain_recall.RecallRecord(
        source_path=source_path,
        chunk_ref=chunk_ref,
        content_hash=_content_hash(content),
        as_of=AS_OF,
        scope=scope,
        requires_egress=requires_egress,
    )


def _chunk(
    *,
    source_path: str = SOURCE_PATH,
    chunk_ref: str = "heading:recall-privacy",
    content: str = CONTENT,
    scope: Any = PUBLIC_SCOPE,
    requires_egress: bool = False,
) -> brain_recall.RecallChunk:
    return brain_recall.RecallChunk(
        record=_record(
            source_path=source_path,
            chunk_ref=chunk_ref,
            content=content,
            scope=scope,
            requires_egress=requires_egress,
        ),
        text=content,
    )


def _store(tmp_path: Path) -> SqliteVecStore:
    return SqliteVecStore(state_root=tmp_path / ".ce" / "state")


def test_default_db_path_creates_file_under_ce_state(tmp_path: Path) -> None:
    state_root = tmp_path / ".ce" / "state"
    expected = state_root / "brain" / "recall.sqlite"

    store = SqliteVecStore(state_root=state_root)
    try:
        assert default_recall_db_path(state_root) == expected
        assert store.db_path == expected
        assert expected.is_file()
    finally:
        store.close()


def test_fts5_table_exists_with_chunk_text_column(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        with sqlite3.connect(store.db_path) as conn:
            table = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'recall_fts'"
            ).fetchone()
            columns = [row[1] for row in conn.execute("PRAGMA table_info(recall_fts)")]
    finally:
        store.close()

    assert table == ("recall_fts",)
    assert columns == ["source_path", "chunk_ref", "text"]


def test_upsert_query_round_trip(tmp_path: Path) -> None:
    store = _store(tmp_path)
    record = _record()
    try:
        count = store.upsert(record, (1.0, 0.0, 0.0))
        hits = store.query((1.0, 0.0, 0.0), top_k=1)
    finally:
        store.close()

    assert count == 1
    assert len(hits) == 1
    assert hits[0].record == record
    assert hits[0].score == pytest.approx(1.0)


def test_rebuild_from_source_replaces_store_and_indexes_text(tmp_path: Path) -> None:
    store = _store(tmp_path)
    embedder = DeterministicFakeEmbedder()
    old = _record(chunk_ref="heading:old", content="old text")
    try:
        store.upsert(old, (1.0, 0.0, 0.0))

        result = store.rebuild_from_source(
            [
                _chunk(chunk_ref="heading:z", content="zeta content"),
                _chunk(chunk_ref="heading:a", content="alpha content"),
            ],
            embedder,
        )
        stored = [record.chunk_ref for record in store.records]
        query_vector = embedder.embed(("alpha content",))[0]
        hits = store.query(query_vector, top_k=2)
        with sqlite3.connect(store.db_path) as conn:
            fts_text = conn.execute(
                "SELECT text FROM recall_fts WHERE chunk_ref = ?",
                ("heading:a",),
            ).fetchone()[0]
    finally:
        store.close()

    assert result.to_dict() == {"count": 2, "model_id": "test-deterministic-fake", "dim": 3}
    assert stored == ["heading:a", "heading:z"]
    assert hits[0].record.chunk_ref == "heading:a"
    assert fts_text == "alpha content"
    assert embedder.inputs == [("alpha content", "zeta content"), ("alpha content",)]


def test_rebuild_from_source_derives_wikilink_graph_edges_byte_identically(tmp_path: Path) -> None:
    first = _store(tmp_path / "first")
    second = _store(tmp_path / "second")
    chunks = [
        _chunk(
            source_path="docs/source.md",
            chunk_ref="heading:source",
            content="# Source\n\nFollow [[Target Page]] and [local](target.md#target-page).\n",
        ),
        _chunk(
            source_path="docs/target.md",
            chunk_ref="heading:target-page",
            content="# Target Page\n\nPointer-only graph recall destination.\n",
        ),
    ]
    try:
        first.rebuild_from_source(chunks, DeterministicFakeEmbedder())
        second.rebuild_from_source(reversed(chunks), DeterministicFakeEmbedder())
        with sqlite3.connect(first.db_path) as conn:
            first_edges = conn.execute(
                """
                SELECT from_source_path, from_chunk_ref, edge_type, target_ref,
                       to_source_path, to_chunk_ref
                  FROM recall_edges
              ORDER BY from_source_path, from_chunk_ref, edge_type, target_ref,
                       to_source_path, to_chunk_ref
                """
            ).fetchall()
        with sqlite3.connect(second.db_path) as conn:
            second_edges = conn.execute(
                """
                SELECT from_source_path, from_chunk_ref, edge_type, target_ref,
                       to_source_path, to_chunk_ref
                  FROM recall_edges
              ORDER BY from_source_path, from_chunk_ref, edge_type, target_ref,
                       to_source_path, to_chunk_ref
                """
            ).fetchall()
        source_record = _record(
            source_path="docs/source.md",
            chunk_ref="heading:source",
            content="# Source\n\nFollow [[Target Page]] and [local](target.md#target-page).\n",
        )
        expanded = first.graph_expand(
            (brain_recall.RecallHit(record=source_record, score=1.0),),
            top_k=5,
        )
    finally:
        first.close()
        second.close()

    assert first_edges == second_edges
    assert first_edges == [
        (
            "docs/source.md",
            "heading:source",
            "markdown-link",
            "target.md#target-page",
            "docs/target.md",
            "heading:target-page",
        ),
        (
            "docs/source.md",
            "heading:source",
            "wikilink",
            "Target Page",
            "docs/target.md",
            "heading:target-page",
        ),
    ]
    assert [hit.record.source_path for hit in expanded] == ["docs/target.md"]


def test_privacy_refuses_confidential_scope_with_egress_embedder_without_consent(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        with pytest.raises(brain_recall.BrainRecallPrivacyRefused):
            store.rebuild_from_source(
                [_chunk(scope=CONFIDENTIAL_SCOPE)],
                EgressRequiringFakeEmbedder(),
                allow_confidential_egress=False,
            )
        assert store.records == ()
    finally:
        store.close()


def test_delete_removes_records_and_fts_rows(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = _record(chunk_ref="heading:first")
    second = _record(chunk_ref="heading:second")
    try:
        store.upsert(
            (
                {"record": first, "vector": (1.0, 0.0, 0.0), "text": "first text"},
                {"record": second, "vector": (0.0, 1.0, 0.0), "text": "second text"},
            )
        )

        count = store.delete([(SOURCE_PATH, "heading:first"), first])
        remaining = store.records
        with sqlite3.connect(store.db_path) as conn:
            fts_count = conn.execute(
                "SELECT COUNT(*) FROM recall_fts WHERE chunk_ref = ?",
                ("heading:first",),
            ).fetchone()[0]
    finally:
        store.close()

    assert count == 1
    assert remaining == (second,)
    assert fts_count == 0


def test_query_uses_deterministic_ordering_for_equal_scores(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        store.upsert(
            (
                brain_recall.RecallVector(
                    record=_record(source_path="docs/z.md", chunk_ref="same"),
                    vector=(1.0, 0.0, 0.0),
                ),
                brain_recall.RecallVector(
                    record=_record(source_path="docs/a.md", chunk_ref="same"),
                    vector=(1.0, 0.0, 0.0),
                ),
                brain_recall.RecallVector(
                    record=_record(source_path="docs/a.md", chunk_ref="earlier"),
                    vector=(1.0, 0.0, 0.0),
                ),
            )
        )
        order = [(hit.record.source_path, hit.record.chunk_ref) for hit in store.query((1.0, 0.0, 0.0), top_k=3)]
    finally:
        store.close()

    assert order == [
        ("docs/a.md", "earlier"),
        ("docs/a.md", "same"),
        ("docs/z.md", "same"),
    ]


def test_db_reopen_persists_records_and_vectors(tmp_path: Path) -> None:
    db_path = default_recall_db_path(tmp_path / ".ce" / "state")
    first = SqliteVecStore(db_path)
    record = _record()
    try:
        first.upsert({"record": record, "vector": (0.0, 1.0, 0.0), "text": CONTENT})
    finally:
        first.close()

    second = SqliteVecStore(db_path)
    try:
        hits = second.query((0.0, 1.0, 0.0), top_k=1)
        with sqlite3.connect(db_path) as conn:
            text = conn.execute(
                "SELECT text FROM recall_fts WHERE source_path = ? AND chunk_ref = ?",
                (SOURCE_PATH, "heading:recall-privacy"),
            ).fetchone()[0]
    finally:
        second.close()

    assert hits[0].record == record
    assert hits[0].score == pytest.approx(1.0)
    assert text == CONTENT


def test_dimension_mismatch_fails_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    try:
        store.upsert(_record(), (1.0, 0.0, 0.0))
        with pytest.raises(brain_recall.BrainRecallInvalid):
            store.upsert(_record(chunk_ref="heading:other"), (1.0, 0.0))
        with pytest.raises(brain_recall.BrainRecallInvalid):
            store.query((1.0, 0.0), top_k=1)
    finally:
        store.close()
