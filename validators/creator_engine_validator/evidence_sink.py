"""v3 G-3.5 — the evidence persistence sink.

``file_evidence_sink(root)`` returns an :data:`EvidenceSink` closure that
serializes a run's :class:`~creator_engine_validator.runner.backend.CollectedEvidence`
(the ``AuditOverlayBackend`` hash-chain) into a durable file matching
``schemas/runtime-evidence.schema.yaml`` — the ``runtime-evidence-chain``
wrapper around the records. It persists iff the chain verifies
(``verify_chain() == []``) AND validates against the schema, and otherwise
raises :class:`EvidencePersistRefused` (value-free) and writes nothing.

It is a serializer-with-integrity-gate: it NEVER re-hashes or mutates a record
(the producer's ``content_hash`` / ``prev_hash`` are preserved verbatim), it is
deterministic (same evidence -> identical bytes), and it introduces no
host / port / credential / account identifier. The actual write goes through an
injectable ``write`` seam (the lone live line); CI drives a fake ``write`` so
the sink is exercised with zero live filesystem write.

Defensive posture: this makes the Creator Engine's own runtime audit trail
durable + tamper-evident; it is never an offensive capability.

Boundary (G-3.5 is the LEAF only): wiring this sink into ``run_plan`` and
resolving the run-outcome / terminal-disposition model is G-3.6. A G-3.1
``change-opened`` terminal record is an orchestrator-level run OUTCOME, not a
RunnerBackend ``lifecycle_phase``; the schema enum does not admit it, so the
sink REFUSES such a chain here rather than persist non-conforming evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml

from .runner.backend import CollectedEvidence
from .runtime_evidence_spine import CHAIN_KIND, CONTENT_HASH_FIELD, verify_chain
from .schema import validate_with_schema

#: The durable chain document's grader — the same contract the ``ce_runtime_evidence`` check enforces.
SCHEMA = "schemas/runtime-evidence.schema.yaml"
CONTRACT = "docs/contracts/runtime-evidence.md"
CHAIN_RECORD_TYPE = "runtime_evidence_chain"
SCHEMA_VERSION = "1"
_NOTE_MAXLEN = 1024

#: The injectable write transport: ``(path, text) -> None``.
Writer = Callable[[Path, str], None]


@dataclass(frozen=True)
class PersistedEvidence:
    """A value-free receipt for one persisted runtime-evidence chain."""

    path: Path
    run_id: str
    record_count: int
    tip_content_hash: str


class EvidencePersistRefused(Exception):
    """Raised (value-free) when a ``CollectedEvidence`` cannot be persisted as a conforming chain."""


#: A sink maps a run's collected evidence to a durable persisted-evidence receipt.
EvidenceSink = Callable[[CollectedEvidence], PersistedEvidence]


def _default_write(path: Path, text: str) -> None:  # pragma: no cover - the lone live writer
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_id(records: list[dict[str, Any]]) -> str:
    ids = {str(record.get("run_id", "")) for record in records}
    if "" in ids or len(ids) != 1:
        raise EvidencePersistRefused("evidence records carry no single run_id")
    return ids.pop()


def file_evidence_sink(root: Path, *, write: Writer | None = None) -> EvidenceSink:
    """Return an :data:`EvidenceSink` that persists chains under ``root`` via ``write``.

    The returned closure, on each call, refuses (``EvidencePersistRefused``,
    value-free) an empty / non-uniform-``run_id`` / hash-broken / schema-invalid
    chain and otherwise writes a deterministic ``runtime-evidence-chain`` YAML
    document, returning a :class:`PersistedEvidence` receipt.
    """
    writer: Writer = write if write is not None else _default_write
    root = Path(root)

    def sink(evidence: CollectedEvidence) -> PersistedEvidence:
        records: list[dict[str, Any]] = [dict(record) for record in evidence.records]
        if not records:
            raise EvidencePersistRefused("evidence chain is empty")
        run_id = _run_id(records)
        if verify_chain(records):
            raise EvidencePersistRefused("evidence chain failed hash-chain verification")
        chain_doc: dict[str, Any] = {
            "kind": CHAIN_KIND,
            "record_type": CHAIN_RECORD_TYPE,
            "schema_version": SCHEMA_VERSION,
            "records": records,
            "note": (evidence.note or "")[:_NOTE_MAXLEN],
        }
        path = root / f"{run_id}.runtime-evidence.yaml"
        if validate_with_schema(
            chain_doc, SCHEMA, path, code="runtime_evidence_schema_violation", contract=CONTRACT
        ):
            raise EvidencePersistRefused("evidence chain failed schema conformance")
        text = yaml.safe_dump(chain_doc, sort_keys=True, allow_unicode=True, default_flow_style=False)
        writer(path, text)
        return PersistedEvidence(
            path=path,
            run_id=run_id,
            record_count=len(records),
            tip_content_hash=str(records[-1][CONTENT_HASH_FIELD]),
        )

    return sink
