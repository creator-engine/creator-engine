"""Markdown corpus ingest runtime for the local brain recall store.

The ingest surface is a rebuildable projection: Markdown remains the source of
truth, and the vector store only carries derived recall records plus vectors.
Worker-owned store/embedder modules are imported dynamically when present; the
offline deterministic path stays dependency-free for validator CI.
"""

from __future__ import annotations

import hashlib
import importlib
import math
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import brain_recall
from ._versions import V3_LOCAL_STATE_ROOT

DEFAULT_STATE_ROOT = Path(V3_LOCAL_STATE_ROOT)
DEFAULT_DB_RELATIVE_PATH = Path("brain") / "recall.sqlite"
DEFAULT_SCOPE = "public"
DEFAULT_AS_OF = "1970-01-01T00:00:00Z"

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_AS_OF_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")


class BrainIngestError(Exception):
    code = "CE-BRAIN-INGEST-ERROR"


class BrainIngestRefused(BrainIngestError):
    code = "CE-BRAIN-INGEST-REFUSED"


class BrainIngestInvalid(BrainIngestError):
    code = "CE-BRAIN-INGEST-INVALID"


class BrainIngestPrivacyRefused(BrainIngestRefused):
    code = "CE-BRAIN-INGEST-PRIVACY-REFUSED"


@dataclass(frozen=True)
class IngestReceiptRecord:
    source_path: str
    chunk_ref: str
    content_hash: str
    action: str
    as_of: str

    def to_dict(self) -> dict[str, str]:
        return {
            "source_path": self.source_path,
            "chunk_ref": self.chunk_ref,
            "content_hash": self.content_hash,
            "action": self.action,
            "as_of": self.as_of,
        }


@dataclass(frozen=True)
class IngestResult:
    db_path: Path
    model_id: str
    dim: int
    source_count: int
    chunk_count: int
    embedded_count: int
    skipped_count: int
    deleted_count: int
    records: tuple[IngestReceiptRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "db_path": str(self.db_path),
            "model_id": self.model_id,
            "dim": self.dim,
            "source_count": self.source_count,
            "chunk_count": self.chunk_count,
            "embedded_count": self.embedded_count,
            "skipped_count": self.skipped_count,
            "deleted_count": self.deleted_count,
            "records": [record.to_dict() for record in self.records],
        }


@dataclass(frozen=True)
class _TextUpsertEntry(Mapping[str, Any]):
    chunk: brain_recall.RecallChunk
    vector: brain_recall.Vector

    @property
    def record(self) -> brain_recall.RecallRecord:
        return self.chunk.record

    def __getitem__(self, key: str) -> Any:
        if key == "chunk":
            return self.chunk
        if key == "record":
            return self.chunk.record
        if key == "vector":
            return self.vector
        raise KeyError(key)

    def __iter__(self):
        return iter(("chunk", "record", "vector"))

    def __len__(self) -> int:
        return 3


def default_db_path(state_root: Path | str | None = None) -> Path:
    root = Path(state_root) if state_root is not None else DEFAULT_STATE_ROOT
    return root / DEFAULT_DB_RELATIVE_PATH


def discover_markdown_files(sources: Sequence[Path | str]) -> tuple[Path, ...]:
    if not sources:
        raise BrainIngestInvalid("at least one --source path is required")
    files: dict[str, Path] = {}
    for raw_source in sources:
        source = Path(raw_source)
        if not source.exists():
            raise BrainIngestInvalid(f"source does not exist: {source}")
        if source.is_file():
            if source.suffix != ".md":
                raise BrainIngestInvalid(f"source file must end in .md: {source}")
            files[str(source.resolve())] = source.resolve()
            continue
        if source.is_dir():
            for candidate in source.rglob("*.md"):
                if candidate.is_file():
                    files[str(candidate.resolve())] = candidate.resolve()
            continue
        raise BrainIngestInvalid(f"source must be a file or directory: {source}")
    return tuple(files[key] for key in sorted(files))


def build_recall_chunks(
    sources: Sequence[Path | str],
    *,
    scope: brain_recall.Scope = DEFAULT_SCOPE,
    repo_root: Path | str | None = None,
    as_of: str | None = None,
) -> tuple[brain_recall.RecallChunk, ...]:
    files = discover_markdown_files(sources)
    root = Path(repo_root).resolve() if repo_root is not None else _find_repo_root(Path.cwd())
    source_base = _source_base(files)
    snapshot_as_of = _normalize_as_of(as_of)
    chunks: list[brain_recall.RecallChunk] = []
    for path in files:
        source_path = _source_path(path, repo_root=root, source_base=source_base)
        for chunk_ref, content in _chunk_markdown(path.read_text(encoding="utf-8")):
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            record = brain_recall.RecallRecord(
                source_path=source_path,
                chunk_ref=chunk_ref,
                content_hash=content_hash,
                as_of=snapshot_as_of,
                scope=scope,
                requires_egress=False,
            )
            chunks.append(brain_recall.RecallChunk(record=record, text=content))
    return tuple(sorted(chunks, key=lambda chunk: chunk.record.key))


def ingest_markdown(
    *,
    sources: Sequence[Path | str],
    state_root: Path | str | None = None,
    db_path: Path | str | None = None,
    scope: brain_recall.Scope = DEFAULT_SCOPE,
    embedder_name: str = "deterministic",
    model_path: Path | str | None = None,
    allow_confidential_egress: bool = False,
    repo_root: Path | str | None = None,
    as_of: str | None = None,
    store: Any | None = None,
    embedder: Any | None = None,
) -> IngestResult:
    resolved_db_path = Path(db_path) if db_path is not None else default_db_path(state_root)
    source_files = discover_markdown_files(sources)
    chunks = build_recall_chunks(source_files, scope=scope, repo_root=repo_root, as_of=as_of)
    active_embedder = embedder if embedder is not None else make_embedder(embedder_name, model_path=model_path)
    active_store = store if store is not None else open_vector_store(resolved_db_path)

    changed_chunks: list[brain_recall.RecallChunk] = []
    skipped: list[brain_recall.RecallChunk] = []
    for chunk in chunks:
        existing = _lookup_record(active_store, chunk.record.source_path, chunk.record.chunk_ref)
        if existing is not None and existing.content_hash == chunk.record.content_hash:
            skipped.append(chunk)
        else:
            changed_chunks.append(chunk)

    try:
        brain_recall.require_embedding_allowed(
            changed_chunks,
            active_embedder,
            allow_confidential_egress=allow_confidential_egress,
        )
    except brain_recall.BrainRecallPrivacyRefused as exc:
        raise BrainIngestPrivacyRefused(str(exc)) from exc

    vectors: tuple[brain_recall.Vector, ...] = ()
    if changed_chunks:
        raw_vectors = active_embedder.embed(tuple(chunk.text for chunk in changed_chunks))
        vectors = tuple(_normalize_vector(vector) for vector in raw_vectors)
        if len(vectors) != len(changed_chunks):
            raise BrainIngestInvalid("embedder returned a different vector count than input chunk count")
        embedder_dim = int(getattr(active_embedder, "dim", 0))
        if embedder_dim <= 0:
            raise BrainIngestInvalid("embedder dim must be a positive integer")
        if any(len(vector) != embedder_dim for vector in vectors):
            raise BrainIngestInvalid("embedder returned a vector with a dimension different from embedder.dim")
        requires_egress = bool(getattr(active_embedder, "requires_egress", False))
        active_store.upsert(
            tuple(
                _TextUpsertEntry(
                    chunk=brain_recall.RecallChunk(
                        record=_record_with_egress(chunk.record, requires_egress),
                        text=chunk.text,
                    ),
                    vector=vector,
                )
                for chunk, vector in zip(changed_chunks, vectors, strict=True)
            )
        )

    deleted_count = _delete_stale_chunks(active_store, chunks)
    receipt_records = tuple(
        sorted(
            (
                IngestReceiptRecord(
                    source_path=chunk.record.source_path,
                    chunk_ref=chunk.record.chunk_ref,
                    content_hash=chunk.record.content_hash,
                    action=action,
                    as_of=chunk.record.as_of,
                )
                for action, selected in (("upserted", changed_chunks), ("skipped", skipped))
                for chunk in selected
            ),
            key=lambda record: (record.source_path, record.chunk_ref, record.action),
        )
    )
    return IngestResult(
        db_path=resolved_db_path,
        model_id=str(getattr(active_embedder, "model_id", embedder_name)),
        dim=int(getattr(active_embedder, "dim", 0)),
        source_count=len(source_files),
        chunk_count=len(chunks),
        embedded_count=len(changed_chunks),
        skipped_count=len(skipped),
        deleted_count=deleted_count,
        records=receipt_records,
    )


def make_embedder(name: str, *, model_path: Path | str | None = None) -> brain_recall.EmbeddingAdapter:
    normalized = name.strip().lower().replace("_", "-")
    if normalized == "deterministic":
        return brain_recall.DeterministicFakeEmbedding()
    if normalized in {"embeddinggemma", "embedding-gemma"}:
        if model_path is None:
            raise BrainIngestInvalid("--model-path is required for --embedder embeddinggemma")
        path = Path(model_path)
        if not path.exists():
            raise BrainIngestInvalid(f"embeddinggemma model path does not exist: {path}")
        return _make_embeddinggemma(path)
    raise BrainIngestInvalid(f"unknown embedder: {name}")


def open_vector_store(db_path: Path | str) -> Any:
    path = Path(db_path)
    try:
        module = importlib.import_module("creator_engine_validator.brain_sqlite_vec")
        store_cls = module.SqliteVecStore
    except (AttributeError, ModuleNotFoundError) as exc:
        raise BrainIngestInvalid("SqliteVecStore adapter module is not available") from exc
    return _call_store_factory(store_cls, path)


def _make_embeddinggemma(model_path: Path) -> brain_recall.EmbeddingAdapter:
    try:
        module = importlib.import_module("creator_engine_validator.brain_embedding_gemma")
    except ModuleNotFoundError as exc:
        raise BrainIngestInvalid("embeddinggemma adapter module is not available") from exc
    for factory_name in ("from_model_path", "create_embedder", "load_embedder"):
        factory = getattr(module, factory_name, None)
        if callable(factory):
            return _call_embedder_factory(factory, model_path)
    for class_name in (
        "EmbeddingGemmaAdapter",
        "GemmaEmbeddingAdapter",
        "BrainEmbeddingGemma",
        "EmbeddingGemma",
    ):
        embedder_cls = getattr(module, class_name, None)
        if embedder_cls is not None:
            return _call_embedder_factory(embedder_cls, model_path)
    raise BrainIngestInvalid("embeddinggemma adapter module exposes no known factory")


def _call_store_factory(factory: Any, path: Path) -> Any:
    for args, kwargs in (
        ((path,), {}),
        ((), {"db_path": path}),
        ((), {"path": path}),
        ((str(path),), {}),
        ((), {"db_path": str(path)}),
    ):
        try:
            return factory(*args, **kwargs)
        except TypeError:
            continue
    return factory(path)


def _call_embedder_factory(factory: Any, model_path: Path) -> brain_recall.EmbeddingAdapter:
    for args, kwargs in (
        ((model_path,), {}),
        ((), {"model_path": model_path}),
        ((str(model_path),), {}),
        ((), {"model_path": str(model_path)}),
    ):
        try:
            return factory(*args, **kwargs)
        except TypeError:
            continue
    return factory(model_path)


def _lookup_record(store: Any, source_path: str, chunk_ref: str) -> brain_recall.RecallRecord | None:
    for method_name in ("lookup_record", "get_record", "find_record", "record_for"):
        method = getattr(store, method_name, None)
        if callable(method):
            value = _call_lookup(method, source_path, chunk_ref)
            if value is not None:
                return _coerce_record(value)
    records = getattr(store, "records", None)
    if callable(records):
        records = records()
    if records is not None:
        for raw_record in records:
            record = _coerce_record(raw_record)
            if record.source_path == source_path and record.chunk_ref == chunk_ref:
                return record
    entries = getattr(store, "entries", None)
    if callable(entries):
        entries = entries()
    if entries is not None:
        for entry in entries:
            raw_record = getattr(entry, "record", None)
            if raw_record is None and isinstance(entry, Mapping):
                raw_record = entry.get("record") or entry.get("entry")
            if raw_record is None:
                continue
            record = _coerce_record(raw_record)
            if record.source_path == source_path and record.chunk_ref == chunk_ref:
                return record
    return None


def _call_lookup(method: Any, source_path: str, chunk_ref: str) -> Any:
    for args, kwargs in (
        ((source_path, chunk_ref), {}),
        ((), {"source_path": source_path, "chunk_ref": chunk_ref}),
        ((brain_recall.RecallKey(source_path, chunk_ref),), {}),
        (((source_path, chunk_ref),), {}),
    ):
        try:
            return method(*args, **kwargs)
        except TypeError:
            continue
    return None


def _delete_stale_chunks(store: Any, chunks: Sequence[brain_recall.RecallChunk]) -> int:
    delete = getattr(store, "delete", None)
    if not callable(delete):
        return 0
    current_keys = {chunk.record.key for chunk in chunks}
    source_paths = {chunk.record.source_path for chunk in chunks}
    stale: list[brain_recall.RecallKey] = []
    records = getattr(store, "records", None)
    if callable(records):
        records = records()
    if records is None:
        return 0
    for raw_record in records:
        record = _coerce_record(raw_record)
        if record.source_path in source_paths and record.key not in current_keys:
            stale.append(record.key)
    return int(delete(stale)) if stale else 0


def _chunk_markdown(text: str) -> tuple[tuple[str, str], ...]:
    normalized = _normalize_newlines(text)
    lines = normalized.splitlines()
    heading_indexes = [idx for idx, line in enumerate(lines) if _HEADING_RE.match(line)]
    if not heading_indexes:
        content = _canonical_chunk_text(lines)
        return (("file", content),) if content else ()

    chunks: list[tuple[str, str]] = []
    if heading_indexes[0] > 0:
        content = _canonical_chunk_text(lines[: heading_indexes[0]])
        if content:
            chunks.append(("preamble", content))

    seen: dict[str, int] = {}
    for pos, start in enumerate(heading_indexes):
        end = heading_indexes[pos + 1] if pos + 1 < len(heading_indexes) else len(lines)
        match = _HEADING_RE.match(lines[start])
        assert match is not None
        slug = _heading_slug(match.group(2))
        seen[slug] = seen.get(slug, 0) + 1
        chunk_ref = f"heading:{slug}" if seen[slug] == 1 else f"heading:{slug}-{seen[slug]}"
        content = _canonical_chunk_text(lines[start:end])
        if content:
            chunks.append((chunk_ref, content))
    return tuple(chunks)


def _canonical_chunk_text(lines: Sequence[str]) -> str:
    stripped = [line.rstrip() for line in lines]
    while stripped and not stripped[0]:
        stripped.pop(0)
    while stripped and not stripped[-1]:
        stripped.pop()
    return ("\n".join(stripped) + "\n") if stripped else ""


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _heading_slug(value: str) -> str:
    slug = _SLUG_RE.sub("-", value.strip().lower()).strip("-")
    return slug or "section"


def _source_path(path: Path, *, repo_root: Path, source_base: Path) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(repo_root)
    except ValueError:
        relative = resolved.relative_to(source_base)
    value = relative.as_posix()
    if not value.endswith(".md") or value.startswith("../") or value.startswith("/"):
        raise BrainIngestInvalid(f"source_path must be relative and end in .md: {value}")
    return value


def _source_base(files: Sequence[Path]) -> Path:
    if not files:
        return Path.cwd().resolve()
    common = Path(os.path.commonpath([str(path.parent) for path in files]))
    return common.resolve()


def _find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() and ((candidate / ".ce").exists() or (candidate / "validators").exists()):
            return candidate
    return current


def _normalize_as_of(value: str | None) -> str:
    if value is None:
        return DEFAULT_AS_OF
    if not isinstance(value, str) or not _AS_OF_RE.match(value):
        raise BrainIngestInvalid("as_of must match YYYY-MM-DDTHH:MM:SSZ")
    return value


def _record_with_egress(record: brain_recall.RecallRecord, requires_egress: bool) -> brain_recall.RecallRecord:
    if record.requires_egress == bool(requires_egress):
        return record
    return brain_recall.RecallRecord(
        source_path=record.source_path,
        chunk_ref=record.chunk_ref,
        content_hash=record.content_hash,
        as_of=record.as_of,
        scope=record.scope,
        requires_egress=bool(requires_egress),
    )


def _coerce_record(value: Any) -> brain_recall.RecallRecord:
    if isinstance(value, brain_recall.RecallRecord):
        return value
    if isinstance(value, brain_recall.RecallVector):
        return value.record
    if isinstance(value, Mapping):
        if "record" in value and isinstance(value["record"], Mapping):
            return brain_recall.RecallRecord.from_mapping(value["record"])
        if "entry" in value and isinstance(value["entry"], Mapping):
            return brain_recall.RecallRecord.from_mapping(value["entry"])
        return brain_recall.RecallRecord.from_mapping(value)
    record = getattr(value, "record", None)
    if record is not None:
        return _coerce_record(record)
    raise BrainIngestInvalid(f"store returned unsupported record value: {type(value)!r}")


def _normalize_vector(vector: Sequence[float]) -> brain_recall.Vector:
    if isinstance(vector, (str, bytes)):
        raise BrainIngestInvalid("vector must be a non-empty numeric sequence")
    values: list[float] = []
    try:
        iterator = iter(vector)
    except TypeError as exc:
        raise BrainIngestInvalid("vector must be a non-empty numeric sequence") from exc
    for raw in iterator:
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise BrainIngestInvalid("vector must contain only numeric values") from exc
        if not math.isfinite(value):
            raise BrainIngestInvalid("vector must contain only finite numeric values")
        values.append(value)
    if not values:
        raise BrainIngestInvalid("vector must be a non-empty numeric sequence")
    return tuple(values)


__all__ = [
    "BrainIngestError",
    "BrainIngestInvalid",
    "BrainIngestPrivacyRefused",
    "BrainIngestRefused",
    "DEFAULT_AS_OF",
    "DEFAULT_DB_RELATIVE_PATH",
    "DEFAULT_SCOPE",
    "IngestReceiptRecord",
    "IngestResult",
    "build_recall_chunks",
    "default_db_path",
    "discover_markdown_files",
    "ingest_markdown",
    "make_embedder",
    "open_vector_store",
]
