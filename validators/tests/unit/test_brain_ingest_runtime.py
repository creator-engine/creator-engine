from __future__ import annotations

import json
import hashlib
import sqlite3
from pathlib import Path

import pytest

from creator_engine_validator import brain_ingest_runtime as rt
from creator_engine_validator import brain_recall
from creator_engine_validator.brain_sqlite_vec import SqliteVecStore

AS_OF = "2026-06-21T00:00:00Z"


class CountingEmbedder:
    requires_egress = False
    model_id = "unit-counting"
    dim = 3

    def __init__(self) -> None:
        self.inputs: list[tuple[str, ...]] = []

    def embed(self, texts) -> tuple[tuple[float, float, float], ...]:
        values = tuple(texts)
        self.inputs.append(values)
        return tuple((float(len(text)), float(idx), float(text.count("\n"))) for idx, text in enumerate(values))


class EgressCountingEmbedder(CountingEmbedder):
    requires_egress = True
    model_id = "unit-egress"


class CaptureStore:
    def __init__(self) -> None:
        self.entries: dict[brain_recall.RecallKey, brain_recall.RecallVector] = {}
        self.upsert_calls: list[tuple[brain_recall.RecallVector, ...]] = []

    def upsert(self, entries) -> int:
        vectors = tuple(entries)
        self.upsert_calls.append(vectors)
        for vector in vectors:
            self.entries[vector.record.key] = vector
        return len(vectors)

    def lookup_record(self, source_path: str, chunk_ref: str) -> brain_recall.RecallRecord | None:
        entry = self.entries.get(brain_recall.RecallKey(source_path, chunk_ref))
        return None if entry is None else entry.record

    @property
    def records(self) -> tuple[brain_recall.RecallRecord, ...]:
        return tuple(self.entries[key].record for key in sorted(self.entries))

    def delete(self, keys) -> int:
        count = 0
        for key in keys:
            if key in self.entries:
                del self.entries[key]
                count += 1
        return count


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _receipt_bytes(result: rt.IngestResult) -> bytes:
    return json.dumps(result.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")


def test_build_recall_chunks_discovers_repo_relative_heading_chunks(tmp_path: Path):
    path = _write(
        tmp_path / "docs" / "brain.md",
        "# Alpha\n\nFirst section.\n\n## Beta\n\nSecond section.\n",
    )

    chunks = rt.build_recall_chunks([path], repo_root=tmp_path, as_of=AS_OF)

    assert [(chunk.record.source_path, chunk.record.chunk_ref) for chunk in chunks] == [
        ("docs/brain.md", "heading:alpha"),
        ("docs/brain.md", "heading:beta"),
    ]
    assert chunks[0].text == "# Alpha\n\nFirst section.\n"
    assert chunks[0].record.content_hash == hashlib.sha256(chunks[0].text.encode("utf-8")).hexdigest()
    assert chunks[0].record.as_of == AS_OF


def test_open_vector_store_prefers_worker_sqlite_vec_store(tmp_path: Path):
    store = rt.open_vector_store(tmp_path / ".ce" / "state" / "brain" / "recall.sqlite")

    assert isinstance(store, SqliteVecStore)
    store.close()


def test_ingest_store_round_trip_with_sqlite_vec_store(tmp_path: Path):
    source = _write(tmp_path / "docs" / "brain.md", "# Alpha\n\nFirst section.\n")
    db_path = tmp_path / ".ce" / "state" / "brain" / "recall.sqlite"

    result = rt.ingest_markdown(
        sources=[source],
        db_path=db_path,
        repo_root=tmp_path,
        as_of=AS_OF,
    )
    store = rt.open_vector_store(db_path)

    assert result.source_count == 1
    assert result.chunk_count == 1
    assert result.embedded_count == 1
    assert result.skipped_count == 0
    assert [record.source_path for record in store.records] == ["docs/brain.md"]
    assert store.records[0].content_hash == result.records[0].content_hash
    assert store.query(store.entries[0].vector, top_k=1)[0].record == store.records[0]
    with sqlite3.connect(db_path) as conn:
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'recall_fts'"
        ).fetchone()
        fts_text = conn.execute(
            """
            SELECT text FROM recall_fts
            WHERE source_path = ? AND chunk_ref = ?
            """,
            ("docs/brain.md", "heading:alpha"),
        ).fetchone()
    assert table == ("recall_fts",)
    assert fts_text == ("# Alpha\n\nFirst section.\n",)
    store.close()


def test_idempotent_reingest_skips_unchanged_records(tmp_path: Path):
    source = _write(tmp_path / "brain.md", "One stable file.\n")
    store = CaptureStore()
    embedder = CountingEmbedder()

    first = rt.ingest_markdown(
        sources=[source],
        store=store,
        embedder=embedder,
        repo_root=tmp_path,
        as_of=AS_OF,
    )
    second = rt.ingest_markdown(
        sources=[source],
        store=store,
        embedder=embedder,
        repo_root=tmp_path,
        as_of=AS_OF,
    )

    assert first.embedded_count == 1
    assert second.embedded_count == 0
    assert second.skipped_count == 1
    assert len(embedder.inputs) == 1
    assert second.records[0].action == "skipped"


def test_changed_content_reembeds_and_upserts(tmp_path: Path):
    source = _write(tmp_path / "brain.md", "Original.\n")
    store = CaptureStore()
    embedder = CountingEmbedder()

    rt.ingest_markdown(sources=[source], store=store, embedder=embedder, repo_root=tmp_path, as_of=AS_OF)
    original_hash = store.records[0].content_hash
    source.write_text("Changed.\n", encoding="utf-8")
    result = rt.ingest_markdown(
        sources=[source],
        store=store,
        embedder=embedder,
        repo_root=tmp_path,
        as_of=AS_OF,
    )

    assert result.embedded_count == 1
    assert result.skipped_count == 0
    assert len(embedder.inputs) == 2
    assert store.records[0].content_hash != original_hash
    assert store.records[0].content_hash == result.records[0].content_hash


def test_receipt_bytes_are_deterministic_for_same_inputs(tmp_path: Path):
    _write(tmp_path / "docs" / "b.md", "Bee.\n")
    _write(tmp_path / "docs" / "a.md", "Aye.\n")

    first = rt.ingest_markdown(
        sources=[tmp_path / "docs"],
        store=CaptureStore(),
        embedder=CountingEmbedder(),
        repo_root=tmp_path,
        as_of=AS_OF,
    )
    second = rt.ingest_markdown(
        sources=[tmp_path / "docs"],
        store=CaptureStore(),
        embedder=CountingEmbedder(),
        repo_root=tmp_path,
        as_of=AS_OF,
    )

    assert _receipt_bytes(first) == _receipt_bytes(second)
    assert [record.source_path for record in first.records] == ["docs/a.md", "docs/b.md"]


def test_confidential_scope_with_egress_embedder_fails_before_embedding(tmp_path: Path):
    source = _write(tmp_path / "brain.md", "Confidential content.\n")
    store = CaptureStore()
    embedder = EgressCountingEmbedder()

    with pytest.raises(rt.BrainIngestPrivacyRefused):
        rt.ingest_markdown(
            sources=[source],
            store=store,
            embedder=embedder,
            scope="confidential",
            repo_root=tmp_path,
            as_of=AS_OF,
        )

    assert embedder.inputs == []
    assert store.records == ()
