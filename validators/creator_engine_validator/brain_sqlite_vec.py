"""SQLite-backed company-brain recall vector store.

The database is derived state: Markdown remains the source of truth and this
store can be rebuilt from source chunks at any time.
"""

from __future__ import annotations

import importlib.util
import json
import math
import posixpath
import re
import sqlite3
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from ._versions import V3_LOCAL_STATE_ROOT
from .brain_recall import (
    BrainRecallInvalid,
    EmbeddingAdapter,
    RecallChunk,
    RecallHit,
    RecallKey,
    RecallRecord,
    RecallVector,
    RebuildResult,
    VectorStoreAdapter,
    _cosine,
    _normalize_chunk,
    _normalize_key,
    _normalize_recall_vector,
    _normalize_vector,
    _record_with_egress,
    _stable_json,
    require_embedding_allowed,
)

SCHEMA_VERSION = "1"
METADATA_SCHEMA_VERSION = "schema_version"
METADATA_VECTOR_BACKEND = "vector_backend"
METADATA_VECTOR_DIM = "vector_dim"
METADATA_VECTOR_MODEL_ID = "vector_model_id"
METADATA_SQLITE_VEC_AVAILABLE = "sqlite_vec_available"
GRAPH_EDGE_WIKILINK = "wikilink"
GRAPH_EDGE_MARKDOWN_LINK = "markdown-link"
_GRAPH_RRF_K = 60


def default_recall_db_path(state_root: Path | str = V3_LOCAL_STATE_ROOT) -> Path:
    """Return the default derived recall DB path under the CE local state root."""

    return Path(state_root) / "brain" / "recall.sqlite"


@dataclass(frozen=True)
class _PreparedEntry:
    record: RecallRecord
    vector: tuple[float, ...]
    text: str | None


@dataclass(frozen=True, order=True)
class GraphEdge:
    """One resolved markdown graph edge, derived from source chunk text."""

    from_source_path: str
    from_chunk_ref: str
    edge_type: str
    target_ref: str
    to_source_path: str
    to_chunk_ref: str


class SqliteVecStore(VectorStoreAdapter):
    """Durable SQLite implementation of the F6.1 vector-store adapter."""

    def __init__(
        self,
        db_path: Path | str | None = None,
        *,
        state_root: Path | str = V3_LOCAL_STATE_ROOT,
    ) -> None:
        self.db_path = Path(db_path) if db_path is not None else default_recall_db_path(state_root)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._initialize()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> SqliteVecStore:
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()

    def upsert(
        self,
        entries: Iterable[RecallVector] | RecallVector | RecallRecord | Mapping[str, Any],
        vector: Sequence[float] | None = None,
        *,
        model_id: str | None = None,
    ) -> int:
        prepared = tuple(self._prepare_entries(entries, vector=vector))
        if not prepared:
            return 0
        with self._conn:
            # Persist the embedding model identity alongside the dimension so the
            # recall surface can fail closed on a same-dimension wrong-model query
            # (a different model that happens to share the dim is still a different
            # vector space). The dim is recorded per-entry by `_require_dim`; the
            # model_id is recorded here from the ingesting embedder.
            if model_id is not None:
                self._require_model_id(str(model_id))
            for entry in prepared:
                self._upsert_one(entry)
            self._refresh_graph_edges_for_sources(
                {entry.record.source_path for entry in prepared}
            )
            self._set_metadata("entry_count", str(self._count_entries()))
        return len(prepared)

    def query(self, vector: Sequence[float], top_k: int = 5) -> tuple[RecallHit, ...]:
        if top_k <= 0 or self._count_entries() == 0:
            return ()
        query_vector = _normalize_vector(vector)
        self._require_dim(len(query_vector))
        hits: list[RecallHit] = []
        for row in self._conn.execute(
            """
            SELECT source_path, chunk_ref, content_hash, as_of, scope_json,
                   requires_egress, vector_json
              FROM recall_entries
            """
        ):
            record = self._record_from_row(row)
            stored_vector = _normalize_vector(json.loads(row["vector_json"]))
            hits.append(RecallHit(record=record, score=_cosine(query_vector, stored_vector)))
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

    def keyword_search(self, query_text: str, top_k: int = 5) -> tuple[RecallHit, ...]:
        """Query the FTS5 keyword index, returning BM25-ranked recall hits.

        F6.2 populated the ``recall_fts`` column but never queried it; F6.3 turns
        it into the keyword leg of hybrid retrieval. The BM25 score is mapped to a
        descending, non-negative relevance (SQLite returns a lower-is-better cost),
        and ordering is made deterministic by the same key tuple as the semantic
        leg so equal-relevance ties never depend on storage order.
        """

        if top_k <= 0 or self._count_entries() == 0:
            return ()
        match_expr = _fts_match_expression(query_text)
        if match_expr is None:
            return ()
        try:
            rows = self._conn.execute(
                """
                SELECT f.source_path AS source_path,
                       f.chunk_ref AS chunk_ref,
                       bm25(recall_fts) AS rank,
                       e.content_hash AS content_hash,
                       e.as_of AS as_of,
                       e.scope_json AS scope_json,
                       e.requires_egress AS requires_egress
                  FROM recall_fts AS f
                  JOIN recall_entries AS e
                    ON e.source_path = f.source_path
                   AND e.chunk_ref = f.chunk_ref
                 WHERE recall_fts MATCH ?
                """,
                (match_expr,),
            ).fetchall()
        except sqlite3.OperationalError as exc:
            if "fts5" in str(exc).lower() or "no such" in str(exc).lower():
                raise BrainRecallInvalid("SQLite FTS5 support is required for recall keyword search") from exc
            raise
        hits = [
            RecallHit(record=self._record_from_row(row), score=_bm25_relevance(row["rank"]))
            for row in rows
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

    def graph_expand(self, hits: Sequence[RecallHit], top_k: int = 5) -> tuple[RecallHit, ...]:
        """Expand ranked recall hits through resolved markdown graph edges.

        The graph is a derived projection over current recall entries. Expansion
        returns only destination recall records; callers fuse it as an additional
        leg, so graph edges can add context but never inline source content.
        """

        if top_k <= 0 or not hits:
            return ()
        scores: dict[RecallKey, float] = {}
        records: dict[RecallKey, RecallRecord] = {}
        for rank, hit in enumerate(hits):
            source_key = hit.record.key
            edge_rows = self._conn.execute(
                """
                SELECT e.source_path, e.chunk_ref, e.content_hash, e.as_of,
                       e.scope_json, e.requires_egress
                  FROM recall_edges AS g
                  JOIN recall_entries AS e
                    ON e.source_path = g.to_source_path
                   AND e.chunk_ref = g.to_chunk_ref
                 WHERE g.from_source_path = ?
                   AND g.from_chunk_ref = ?
              ORDER BY g.edge_type, g.target_ref, g.to_source_path, g.to_chunk_ref
                """,
                (source_key.source_path, source_key.chunk_ref),
            ).fetchall()
            for edge_index, row in enumerate(edge_rows):
                record = self._record_from_row(row)
                if record.key == source_key:
                    continue
                edge_score = 1.0 / (_GRAPH_RRF_K + rank + 1 + (edge_index * 0.001))
                scores[record.key] = scores.get(record.key, 0.0) + edge_score
                records.setdefault(record.key, record)
        ordered = sorted(
            scores.items(),
            key=lambda item: (
                -item[1],
                item[0].source_path,
                item[0].chunk_ref,
            ),
        )
        return tuple(RecallHit(record=records[key], score=round(score, 12)) for key, score in ordered[:top_k])

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
        vectors = tuple(
            _normalize_vector(vector)
            for vector in embedder.embed(tuple(chunk.text for chunk in source_chunks))
        )
        if len(vectors) != len(source_chunks):
            raise BrainRecallInvalid("embedder returned a different vector count than input text count")
        if any(len(vector) != embedder.dim for vector in vectors):
            raise BrainRecallInvalid("embedder returned a vector with a dimension different from embedder.dim")

        requires_egress = bool(getattr(embedder, "requires_egress", False))
        prepared = tuple(
            _PreparedEntry(
                record=_record_with_egress(chunk.record, requires_egress),
                vector=vector,
                text=chunk.text,
            )
            for chunk, vector in zip(source_chunks, vectors, strict=True)
        )
        with self._conn:
            self._conn.execute("DELETE FROM recall_edges")
            self._conn.execute("DELETE FROM recall_fts")
            self._conn.execute("DELETE FROM recall_entries")
            self._set_metadata(METADATA_VECTOR_DIM, str(embedder.dim))
            self._set_metadata(METADATA_VECTOR_MODEL_ID, str(embedder.model_id))
            for entry in prepared:
                self._upsert_one(entry)
            self._rebuild_graph_edges_from_prepared(prepared)
            self._set_metadata("entry_count", str(len(prepared)))
        return RebuildResult(count=len(source_chunks), model_id=embedder.model_id, dim=embedder.dim)

    def delete(self, keys: Iterable[RecallKey | RecallRecord | tuple[str, str]]) -> int:
        count = 0
        with self._conn:
            for raw_key in keys:
                key = _normalize_key(raw_key)
                cursor = self._conn.execute(
                    "DELETE FROM recall_entries WHERE source_path = ? AND chunk_ref = ?",
                    (key.source_path, key.chunk_ref),
                )
                if cursor.rowcount:
                    self._delete_fts(key)
                    self._delete_graph_edges(key)
                    count += cursor.rowcount
            remaining = self._count_entries()
            self._set_metadata("entry_count", str(remaining))
            if remaining == 0:
                self._delete_metadata(METADATA_VECTOR_DIM)
                self._delete_metadata(METADATA_VECTOR_MODEL_ID)
                self._conn.execute("DELETE FROM recall_edges")
        return count

    @property
    def entries(self) -> tuple[RecallVector, ...]:
        return tuple(
            RecallVector(record=self._record_from_row(row), vector=json.loads(row["vector_json"]))
            for row in self._conn.execute(
                """
                SELECT source_path, chunk_ref, content_hash, as_of, scope_json,
                       requires_egress, vector_json
                  FROM recall_entries
              ORDER BY source_path, chunk_ref
                """
            )
        )

    @property
    def records(self) -> tuple[RecallRecord, ...]:
        return tuple(entry.record for entry in self.entries)

    @property
    def dim(self) -> int | None:
        raw = self._metadata(METADATA_VECTOR_DIM)
        return int(raw) if raw is not None else None

    @property
    def model_id(self) -> str | None:
        return self._metadata(METADATA_VECTOR_MODEL_ID)

    def _initialize(self) -> None:
        try:
            with self._conn:
                self._conn.execute("PRAGMA foreign_keys = ON")
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS recall_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    ) WITHOUT ROWID
                    """
                )
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS recall_entries (
                        source_path TEXT NOT NULL,
                        chunk_ref TEXT NOT NULL,
                        content_hash TEXT NOT NULL,
                        as_of TEXT NOT NULL,
                        scope_json TEXT NOT NULL,
                        requires_egress INTEGER NOT NULL CHECK (requires_egress IN (0, 1)),
                        text TEXT NOT NULL,
                        vector_json TEXT NOT NULL,
                        dim INTEGER NOT NULL CHECK (dim > 0),
                        PRIMARY KEY (source_path, chunk_ref)
                    ) WITHOUT ROWID
                    """
                )
                self._conn.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS recall_fts
                    USING fts5(source_path UNINDEXED, chunk_ref UNINDEXED, text)
                    """
                )
                self._conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS recall_edges (
                        from_source_path TEXT NOT NULL,
                        from_chunk_ref TEXT NOT NULL,
                        edge_type TEXT NOT NULL,
                        target_ref TEXT NOT NULL,
                        to_source_path TEXT NOT NULL,
                        to_chunk_ref TEXT NOT NULL,
                        PRIMARY KEY (
                            from_source_path, from_chunk_ref, edge_type,
                            target_ref, to_source_path, to_chunk_ref
                        ),
                        FOREIGN KEY (from_source_path, from_chunk_ref)
                            REFERENCES recall_entries(source_path, chunk_ref)
                            ON DELETE CASCADE,
                        FOREIGN KEY (to_source_path, to_chunk_ref)
                            REFERENCES recall_entries(source_path, chunk_ref)
                            ON DELETE CASCADE
                    ) WITHOUT ROWID
                    """
                )
                self._set_metadata(METADATA_SCHEMA_VERSION, SCHEMA_VERSION)
                self._set_metadata(METADATA_VECTOR_BACKEND, "python-cosine-json")
                self._set_metadata(
                    METADATA_SQLITE_VEC_AVAILABLE,
                    "true" if importlib.util.find_spec("sqlite_vec") is not None else "false",
                )
                self._set_metadata("entry_count", str(self._count_entries()))
        except sqlite3.OperationalError as exc:
            if "fts5" in str(exc).lower():
                raise BrainRecallInvalid("SQLite FTS5 support is required for recall text indexing") from exc
            raise

    def _prepare_entries(
        self,
        entries: Iterable[RecallVector] | RecallVector | RecallRecord | Mapping[str, Any],
        *,
        vector: Sequence[float] | None,
    ) -> Iterable[_PreparedEntry]:
        if vector is not None:
            text = None
            record: Any = entries
            if isinstance(entries, Mapping):
                if "record" in entries:
                    record = entries["record"]
                text = self._text_from_mapping(entries)
            if isinstance(record, Mapping):
                record = RecallRecord.from_mapping(record)
            if not isinstance(record, RecallRecord):
                raise BrainRecallInvalid("record must be a RecallRecord or mapping")
            yield _PreparedEntry(
                record=record,
                vector=_normalize_vector(vector),
                text=text,
            )
            return
        if isinstance(entries, RecallVector) or isinstance(entries, Mapping):
            yield self._prepare_entry(entries)
            return
        for raw_entry in entries:
            yield self._prepare_entry(raw_entry)

    def _prepare_entry(self, raw_entry: Any) -> _PreparedEntry:
        text = self._text_from_mapping(raw_entry) if isinstance(raw_entry, Mapping) else None
        if isinstance(raw_entry, Mapping) and "chunk" in raw_entry and "vector" in raw_entry:
            chunk = _normalize_chunk(raw_entry["chunk"])
            text = chunk.text if text is None else text
            vector = _normalize_vector(raw_entry["vector"])
            return _PreparedEntry(record=chunk.record, vector=vector, text=text)
        entry = _normalize_recall_vector(raw_entry)
        return _PreparedEntry(record=entry.record, vector=entry.vector, text=text)

    def _upsert_one(self, entry: _PreparedEntry) -> None:
        self._require_dim(len(entry.vector))
        key = entry.record.key
        text = entry.text
        if text is None:
            row = self._conn.execute(
                "SELECT text FROM recall_entries WHERE source_path = ? AND chunk_ref = ?",
                (key.source_path, key.chunk_ref),
            ).fetchone()
            text = row["text"] if row is not None else ""
        if not isinstance(text, str):
            raise BrainRecallInvalid("text must be a string")
        scope_json = _stable_json(entry.record.scope)
        vector_json = _stable_json(entry.vector)
        self._conn.execute(
            """
            INSERT INTO recall_entries (
                source_path, chunk_ref, content_hash, as_of, scope_json,
                requires_egress, text, vector_json, dim
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_path, chunk_ref) DO UPDATE SET
                content_hash = excluded.content_hash,
                as_of = excluded.as_of,
                scope_json = excluded.scope_json,
                requires_egress = excluded.requires_egress,
                text = excluded.text,
                vector_json = excluded.vector_json,
                dim = excluded.dim
            """,
            (
                key.source_path,
                key.chunk_ref,
                entry.record.content_hash,
                entry.record.as_of,
                scope_json,
                1 if entry.record.requires_egress else 0,
                text,
                vector_json,
                len(entry.vector),
            ),
        )
        self._replace_fts(key, text)

    def _require_dim(self, dim: int) -> None:
        stored_dim = self.dim
        if stored_dim is None:
            self._set_metadata(METADATA_VECTOR_DIM, str(dim))
            return
        if stored_dim != dim:
            raise BrainRecallInvalid("vector dimension does not match the store dimension")

    def _require_model_id(self, model_id: str) -> None:
        stored_model_id = self.model_id
        if stored_model_id is None:
            self._set_metadata(METADATA_VECTOR_MODEL_ID, model_id)
            return
        if stored_model_id != model_id:
            raise BrainRecallInvalid(
                "vector model identity does not match the store model: store was built with "
                f"model_id={stored_model_id!r} but this upsert uses model_id={model_id!r}"
            )

    def _replace_fts(self, key: RecallKey, text: str) -> None:
        self._delete_fts(key)
        self._conn.execute(
            "INSERT INTO recall_fts(source_path, chunk_ref, text) VALUES (?, ?, ?)",
            (key.source_path, key.chunk_ref, text),
        )

    def _delete_fts(self, key: RecallKey) -> None:
        self._conn.execute(
            "DELETE FROM recall_fts WHERE source_path = ? AND chunk_ref = ?",
            (key.source_path, key.chunk_ref),
        )

    def _refresh_graph_edges_for_sources(self, source_paths: set[str]) -> None:
        if not source_paths:
            return
        self._conn.execute("DELETE FROM recall_edges")
        entries = self._entries_with_text()
        self._insert_graph_edges(_derive_graph_edges(entries))

    def _rebuild_graph_edges_from_prepared(self, prepared: Sequence[_PreparedEntry]) -> None:
        entries = tuple(
            (entry.record, entry.text)
            for entry in sorted(prepared, key=lambda item: item.record.key)
            if entry.text is not None
        )
        self._insert_graph_edges(_derive_graph_edges(entries))

    def _insert_graph_edges(self, edges: Iterable[GraphEdge]) -> None:
        for edge in sorted(set(edges)):
            self._conn.execute(
                """
                INSERT OR IGNORE INTO recall_edges (
                    from_source_path, from_chunk_ref, edge_type, target_ref,
                    to_source_path, to_chunk_ref
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    edge.from_source_path,
                    edge.from_chunk_ref,
                    edge.edge_type,
                    edge.target_ref,
                    edge.to_source_path,
                    edge.to_chunk_ref,
                ),
            )

    def _delete_graph_edges(self, key: RecallKey) -> None:
        self._conn.execute(
            """
            DELETE FROM recall_edges
             WHERE from_source_path = ?
               AND from_chunk_ref = ?
            """,
            (key.source_path, key.chunk_ref),
        )
        self._conn.execute(
            """
            DELETE FROM recall_edges
             WHERE to_source_path = ?
               AND to_chunk_ref = ?
            """,
            (key.source_path, key.chunk_ref),
        )

    def _entries_with_text(self) -> tuple[tuple[RecallRecord, str], ...]:
        rows = self._conn.execute(
            """
            SELECT source_path, chunk_ref, content_hash, as_of, scope_json,
                   requires_egress, text
              FROM recall_entries
          ORDER BY source_path, chunk_ref
            """
        ).fetchall()
        return tuple((self._record_from_row(row), str(row["text"])) for row in rows)

    def _record_from_row(self, row: sqlite3.Row) -> RecallRecord:
        return RecallRecord(
            source_path=row["source_path"],
            chunk_ref=row["chunk_ref"],
            content_hash=row["content_hash"],
            as_of=row["as_of"],
            scope=json.loads(row["scope_json"]),
            requires_egress=bool(row["requires_egress"]),
        )

    def _count_entries(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS count FROM recall_entries").fetchone()
        return int(row["count"])

    def _metadata(self, key: str) -> str | None:
        row = self._conn.execute("SELECT value FROM recall_metadata WHERE key = ?", (key,)).fetchone()
        return str(row["value"]) if row is not None else None

    def _set_metadata(self, key: str, value: str) -> None:
        self._conn.execute(
            """
            INSERT INTO recall_metadata(key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )

    def _delete_metadata(self, key: str) -> None:
        self._conn.execute("DELETE FROM recall_metadata WHERE key = ?", (key,))

    def _text_from_mapping(self, value: Mapping[str, Any]) -> str | None:
        if "text" not in value:
            return None
        text = value["text"]
        if not isinstance(text, str):
            raise BrainRecallInvalid("text must be a string")
        return text


SqliteVectorStore = SqliteVecStore


_FTS_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_GRAPH_SLUG_RE = re.compile(r"[^a-z0-9]+")
_WIKILINK_RE = re.compile(r"\[\[([^\]\n]+)\]\]")
_MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]\n]*\]\(([^)\n]+)\)")


@dataclass(frozen=True)
class _GraphIndex:
    sources: frozenset[str]
    source_aliases: Mapping[str, str | None]
    preferred_chunk_by_source: Mapping[str, RecallKey]
    chunk_by_source_heading: Mapping[tuple[str, str], RecallKey]
    chunk_by_unique_heading: Mapping[str, RecallKey | None]


def _derive_graph_edges(
    entries: Sequence[tuple[RecallRecord, str | None]],
    *,
    from_sources: set[str] | None = None,
) -> tuple[GraphEdge, ...]:
    index = _build_graph_index(entries)
    selected_sources = set(from_sources) if from_sources is not None else None
    edges: list[GraphEdge] = []
    for record, text in sorted(entries, key=lambda item: item[0].key):
        if selected_sources is not None and record.source_path not in selected_sources:
            continue
        if not text:
            continue
        for edge_type, target_ref in _markdown_graph_targets(text):
            destination = _resolve_graph_target(record.source_path, target_ref, index)
            if destination is None:
                continue
            edges.append(
                GraphEdge(
                    from_source_path=record.source_path,
                    from_chunk_ref=record.chunk_ref,
                    edge_type=edge_type,
                    target_ref=target_ref,
                    to_source_path=destination.source_path,
                    to_chunk_ref=destination.chunk_ref,
                )
            )
    return tuple(sorted(set(edges)))


def _build_graph_index(entries: Sequence[tuple[RecallRecord, str | None]]) -> _GraphIndex:
    records = tuple(sorted((entry[0] for entry in entries), key=lambda record: record.key))
    sources = frozenset(record.source_path for record in records)
    chunks_by_source: dict[str, list[RecallKey]] = defaultdict(list)
    source_alias_candidates: dict[str, list[str]] = defaultdict(list)
    chunk_by_source_heading: dict[tuple[str, str], RecallKey] = {}
    heading_candidates: dict[str, list[RecallKey]] = defaultdict(list)

    for record in records:
        key = record.key
        chunks_by_source[record.source_path].append(key)
        for alias in _source_aliases(record.source_path):
            source_alias_candidates[alias].append(record.source_path)
        heading = _heading_from_chunk_ref(record.chunk_ref)
        if heading is not None:
            chunk_by_source_heading[(record.source_path, heading)] = key
            heading_candidates[heading].append(key)

    source_aliases = {
        alias: candidates[0] if len(set(candidates)) == 1 else None
        for alias, candidates in source_alias_candidates.items()
    }
    preferred_chunk_by_source = {
        source: _preferred_chunk(keys)
        for source, keys in chunks_by_source.items()
    }
    unique_heading = {
        heading: keys[0] if len(set(keys)) == 1 else None
        for heading, keys in heading_candidates.items()
    }
    return _GraphIndex(
        sources=sources,
        source_aliases=source_aliases,
        preferred_chunk_by_source=preferred_chunk_by_source,
        chunk_by_source_heading=chunk_by_source_heading,
        chunk_by_unique_heading=unique_heading,
    )


def _markdown_graph_targets(text: str) -> tuple[tuple[str, str], ...]:
    targets: list[tuple[str, str]] = []
    for match in _WIKILINK_RE.finditer(text):
        target = _clean_wikilink_target(match.group(1))
        if target is not None:
            targets.append((GRAPH_EDGE_WIKILINK, target))
    for match in _MARKDOWN_LINK_RE.finditer(text):
        target = _clean_markdown_link_target(match.group(1))
        if target is not None:
            targets.append((GRAPH_EDGE_MARKDOWN_LINK, target))
    return tuple(targets)


def _resolve_graph_target(from_source_path: str, target_ref: str, index: _GraphIndex) -> RecallKey | None:
    path_part, fragment = _split_graph_target(target_ref)
    if path_part is None and fragment is None:
        return None

    source_path: str | None = None
    if path_part is None:
        source_path = from_source_path
    elif path_part:
        source_path = _resolve_source_path(from_source_path, path_part, index)

    if source_path is not None and fragment is not None:
        return index.chunk_by_source_heading.get((source_path, _graph_slug(fragment)))
    if source_path is not None:
        return index.preferred_chunk_by_source.get(source_path)
    if fragment is not None:
        return index.chunk_by_unique_heading.get(_graph_slug(fragment))

    assert path_part is not None
    alias = _graph_ref_key(path_part)
    resolved_source = index.source_aliases.get(alias)
    if resolved_source is not None:
        return index.preferred_chunk_by_source.get(resolved_source)
    return index.chunk_by_unique_heading.get(alias)


def _resolve_source_path(from_source_path: str, path_part: str, index: _GraphIndex) -> str | None:
    decoded = unquote(path_part).strip()
    if not decoded:
        return None
    candidates: list[str] = []
    if decoded.startswith("/"):
        candidates.append(decoded.lstrip("/"))
    else:
        base = posixpath.dirname(from_source_path)
        candidates.append(posixpath.normpath(posixpath.join(base, decoded)))
        candidates.append(decoded)
    for candidate in tuple(candidates):
        if not candidate.endswith(".md"):
            candidates.append(f"{candidate}.md")
    for candidate in candidates:
        normalized = candidate.lstrip("./")
        if normalized in index.sources:
            return normalized
    return index.source_aliases.get(_graph_ref_key(decoded))


def _split_graph_target(target_ref: str) -> tuple[str | None, str | None]:
    target = target_ref.strip()
    if not target:
        return None, None
    if target.startswith("#"):
        return None, target[1:]
    path_part, sep, fragment = target.partition("#")
    path_part = path_part.strip()
    fragment = fragment.strip() if sep else None
    if not path_part:
        return None, fragment or None
    if sep:
        return path_part, fragment or None
    if "/" in path_part or path_part.endswith(".md"):
        return path_part, None
    # Bare wikilinks can name either a file or a heading; resolve both later.
    return path_part, None


def _clean_wikilink_target(raw_target: str) -> str | None:
    target = raw_target.split("|", 1)[0].strip()
    return target or None


def _clean_markdown_link_target(raw_target: str) -> str | None:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        target = target.split()[0] if target.split() else ""
    if not target:
        return None
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return None
    path = unquote(parsed.path)
    if path and not path.endswith(".md") and not path.startswith("#"):
        return None
    if parsed.fragment:
        return f"{path}#{unquote(parsed.fragment)}" if path else f"#{unquote(parsed.fragment)}"
    return path or None


def _source_aliases(source_path: str) -> set[str]:
    without_ext = source_path[:-3] if source_path.endswith(".md") else source_path
    name = Path(without_ext).name
    return {
        _graph_ref_key(source_path),
        _graph_ref_key(without_ext),
        _graph_ref_key(name),
    }


def _preferred_chunk(keys: Sequence[RecallKey]) -> RecallKey:
    ordered = sorted(
        keys,
        key=lambda key: (
            0 if key.chunk_ref == "file" else 1 if key.chunk_ref == "preamble" else 2,
            key.chunk_ref,
            key.source_path,
        ),
    )
    return ordered[0]


def _heading_from_chunk_ref(chunk_ref: str) -> str | None:
    if not chunk_ref.startswith("heading:"):
        return None
    return chunk_ref.split(":", 1)[1]


def _graph_ref_key(value: str) -> str:
    stripped = value.strip().replace("\\", "/")
    if stripped.endswith(".md"):
        stripped = stripped[:-3]
    return _graph_slug(stripped)


def _graph_slug(value: str) -> str:
    slug = _GRAPH_SLUG_RE.sub("-", value.strip().lower()).strip("-")
    return slug or "section"


def _fts_match_expression(query_text: str) -> str | None:
    """Build a safe FTS5 MATCH expression from free-form context text.

    Tokens are extracted alphanumerically (dropping FTS operators/quotes so user
    text can never inject MATCH syntax), lower-cased for stability, and OR-joined
    so any keyword overlap surfaces a candidate. Returns ``None`` when no usable
    token survives so callers can short-circuit to an empty result.
    """

    if not isinstance(query_text, str):
        raise BrainRecallInvalid("query text must be a string")
    tokens = [token.lower() for token in _FTS_TOKEN_RE.findall(query_text)]
    if not tokens:
        return None
    seen: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.append(token)
    return " OR ".join(f'"{token}"' for token in seen)


def _bm25_relevance(rank: Any) -> float:
    """Map SQLite's lower-is-better bm25 cost to a descending non-negative score."""

    try:
        value = float(rank)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(value):
        return 0.0
    # bm25() returns a negative cost (better matches are more negative). Negate so
    # a larger score is a better match, matching the semantic leg's cosine sign.
    return -value


__all__ = [
    "GRAPH_EDGE_MARKDOWN_LINK",
    "GRAPH_EDGE_WIKILINK",
    "GraphEdge",
    "SCHEMA_VERSION",
    "SqliteVecStore",
    "SqliteVectorStore",
    "default_recall_db_path",
]
