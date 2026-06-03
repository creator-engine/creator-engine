"""Hash-chained runtime-evidence spine (v3 G-1.3a, plane C) — PURE substrate.

The tamper-evident, append-only, content-addressed record chain that the
(deferred, G-1.3b) classifier/audit overlay will write runtime-lifecycle
attestations into. Each record is content-addressed and chain-linked, and is
anchored to the exact runtime-policy it attests via ``policy_sha``.

This REUSES the proven in-repo hash-chain discipline rather than inventing a new
one — it mirrors ``ce_event_runtime`` (content-addressed signed blocks) and
``side_effect_ledger_runtime`` (append-only per-lane hash chain + head manifest):

* **content addressing** — ``content_hash`` is the SHA256 of the canonical JSON
  of the record material *excluding* ``content_hash`` itself (the exact
  ``ce_event_block._canonical_hash`` rule: ``sort_keys=True``, tight separators,
  ``ensure_ascii=False``);
* **chain linkage** — every record carries ``prev_hash``; the genesis record's
  ``prev_hash`` is the all-zero SHA256 sentinel (mirror
  ``side_effect_ledger_runtime.GENESIS_SHA``), and a non-genesis ``prev_hash``
  MUST equal the prior record's ``content_hash``;
* **monotonic sequence** — contiguous from ``0`` at genesis.

**PURE.** ``append`` and ``verify_chain`` operate on in-memory records only — no
disk write, no subprocess, no network, and no wall-clock read (timestamps are
inputs, never read here). Importing this module performs zero I/O. The live event
tap that *produces* these records is the G-1.3b audit overlay, which sits behind
the G-1.2 injectable-runner seam; this substrate never touches a live runtime.

Defensive only — it makes the Creator Engine's own runtime audit trail
tamper-evident; it is never an offensive capability.

See:
  - ``docs/contracts/runtime-evidence.md``
  - ``schemas/runtime-evidence.schema.yaml``
  - ``checks/ce_event_block.py`` / ``ce_event_runtime.py`` (hash-chain provenance)
  - ``side_effect_ledger_runtime.py`` (genesis-sentinel provenance)
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

#: The genesis record has no predecessor: its ``prev_hash`` is the all-zero
#: SHA256 sentinel (mirror ``side_effect_ledger_runtime.GENESIS_SHA``).
GENESIS_PREV_HASH = "0" * 64

#: Discriminators — the ``ce_runtime_evidence`` check self-selects files by
#: ``CHAIN_KIND`` and the schema pins each element to ``RECORD_KIND``.
CHAIN_KIND = "runtime-evidence-chain"
RECORD_KIND = "runtime-evidence-record"

#: The single field excluded from the content-address material.
CONTENT_HASH_FIELD = "content_hash"

#: The RunnerBackend lifecycle phases an evidence record may attest.
LIFECYCLE_PHASES = ("provision", "run", "collect", "teardown")
#: The classifier verdict categories (assigned by the deferred G-1.3b overlay).
CLASSIFICATIONS = ("allowed", "denied", "escalate")

#: Semantic finding kinds returned by :func:`verify_chain`. The check maps these
#: to its own stable error codes — the spine owns the *semantics*, not the codes.
FINDING_KINDS = ("content_address", "chain_link", "sequence", "policy_unbound")

_POLICY_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ChainFinding:
    """One tamper / integrity finding for the record at ``index`` in a chain."""

    kind: str
    index: int
    message: str


def canonical_content_hash(record: dict[str, Any]) -> str:
    """Return the SHA256 of the canonical record material (excludes ``content_hash``).

    Canonicalization is byte-for-byte the ``ce_event_block._canonical_hash`` rule:
    ``json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False)``.
    Deterministic and stdlib-only; performs no I/O.
    """
    material = {k: v for k, v in record.items() if k != CONTENT_HASH_FIELD}
    raw = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def append(chain: Sequence[dict[str, Any]], record_body: dict[str, Any]) -> dict[str, Any]:
    """Return a new chain-linked, content-addressed record to follow ``chain``.

    PURE: does not mutate ``chain`` or ``record_body``. Stamps the computed
    ``sequence`` (``len(chain)``; ``0`` at genesis), ``prev_hash`` (the genesis
    sentinel for an empty chain, else the last record's ``content_hash``), and
    ``content_hash`` (the canonical content address). ``record_body`` supplies
    every semantic field (kind, record_type, schema_version, policy_sha, run_id,
    lifecycle_phase, classification, recorded_at, …).
    """
    record = dict(record_body)
    record.pop(CONTENT_HASH_FIELD, None)
    record["sequence"] = len(chain)
    if chain:
        last = chain[-1]
        record["prev_hash"] = str(last.get(CONTENT_HASH_FIELD) or "") if isinstance(last, dict) else ""
    else:
        record["prev_hash"] = GENESIS_PREV_HASH
    record[CONTENT_HASH_FIELD] = canonical_content_hash(record)
    return record


def verify_chain(records: Sequence[Any]) -> list[ChainFinding]:
    """Return tamper / integrity findings for an in-memory evidence chain.

    Detects, per record: **mutation** (``content_hash`` != recomputed), **reorder
    / truncation** (``sequence`` not contiguous from ``0``), **broken linkage**
    (genesis ``prev_hash`` != sentinel; non-genesis ``prev_hash`` != prior
    ``content_hash``), and **missing policy binding** (``policy_sha`` absent or
    not a 64-hex digest). PURE and deterministic; NEVER raises for a tampered
    chain — it returns findings. An empty list means the chain verifies clean.
    """
    findings: list[ChainFinding] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            findings.append(ChainFinding("content_address", index, f"record[{index}] is not a mapping"))
            continue
        # Mutation: the content address must match the recomputed canonical hash.
        expected_hash = canonical_content_hash(record)
        actual_hash = record.get(CONTENT_HASH_FIELD)
        if actual_hash != expected_hash:
            findings.append(ChainFinding(
                "content_address", index,
                f"content_hash {actual_hash!r} != recomputed {expected_hash} (record mutated after hashing)",
            ))
        # Reorder / truncation: the sequence must be contiguous from 0.
        sequence = record.get("sequence")
        if sequence != index:
            findings.append(ChainFinding(
                "sequence", index,
                f"sequence {sequence!r} != expected {index} (chain reordered or a record was truncated)",
            ))
        # Broken linkage: genesis sentinel, then previous-content-hash binding.
        prev_hash = record.get("prev_hash")
        if index == 0:
            if prev_hash != GENESIS_PREV_HASH:
                findings.append(ChainFinding(
                    "chain_link", index,
                    f"genesis prev_hash {prev_hash!r} != all-zero sentinel {GENESIS_PREV_HASH}",
                ))
        else:
            prior = records[index - 1]
            expected_prev = prior.get(CONTENT_HASH_FIELD) if isinstance(prior, dict) else None
            if prev_hash != expected_prev:
                findings.append(ChainFinding(
                    "chain_link", index,
                    f"prev_hash {prev_hash!r} != prior record content_hash {expected_prev!r} (broken hash chain)",
                ))
        # Policy binding: every record anchors to its runtime-policy via policy_sha.
        policy_sha = record.get("policy_sha")
        if not is_policy_sha(policy_sha):
            findings.append(ChainFinding(
                "policy_unbound", index,
                f"policy_sha {policy_sha!r} is absent or not a 64-hex digest "
                "(record is unbound from the runtime-policy it attests)",
            ))
    return findings


def is_policy_sha(value: Any) -> bool:
    """True when ``value`` is a 64-character lowercase-hex SHA256 digest."""
    return isinstance(value, str) and bool(_POLICY_SHA_RE.match(value))
