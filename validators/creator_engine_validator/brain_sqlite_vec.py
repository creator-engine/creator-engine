"""SQLite-backed company-brain recall vector store.

The database is derived state: Markdown remains the source of truth and this
store can be rebuilt from source chunks at any time.
"""

from __future__ import annotations

import importlib.util
import json
import math
import re
import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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


def default_recall_db_path(state_root: Path | str = V3_LOCAL_STATE_ROOT) -> Path:
    """Return the default derived recall DB path under the CE local state root."""

    return Path(state_root) / "brain" / "recall.sqlite"


@dataclass(frozen=True)
class _PreparedEntry:
    record: RecallRecord
    vector: tuple[float, ...]
    text: str | None


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
    ) -> int:
        prepared = tuple(self._prepare_entries(entries, vector=vector))
        if not prepared:
            return 0
        with self._conn:
            for entry in prepared:
                self._upsert_one(entry)
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
            self._conn.execute("DELETE FROM recall_fts")
            self._conn.execute("DELETE FROM recall_entries")
            self._set_metadata(METADATA_VECTOR_DIM, str(embedder.dim))
            self._set_metadata(METADATA_VECTOR_MODEL_ID, str(embedder.model_id))
            for entry in prepared:
                self._upsert_one(entry)
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
                    count += cursor.rowcount
            remaining = self._count_entries()
            self._set_metadata("entry_count", str(remaining))
            if remaining == 0:
                self._delete_metadata(METADATA_VECTOR_DIM)
                self._delete_metadata(METADATA_VECTOR_MODEL_ID)
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
    "SCHEMA_VERSION",
    "SqliteVecStore",
    "SqliteVectorStore",
    "default_recall_db_path",
]
