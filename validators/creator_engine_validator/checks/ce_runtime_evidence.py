"""Runtime Evidence chain validation and tamper-evidence predicates (v3 G-1.3a).

Dogfood validator for the hash-chained runtime-evidence spine: it validates
*static* Runtime Evidence chain files against
``schemas/runtime-evidence.schema.yaml`` and the tamper-evidence predicates
(content addressing, hash-chain linkage, sequence contiguity, and policy
binding), reusing the PURE ``runtime_evidence_spine`` substrate for the chain
semantics so a validated file is exactly what ``verify_chain`` accepts.

Scope (G-1.3a — substrate / record-shape only): this check NEVER allocates a
container, invokes a runner backend, opens a network socket, or taps a live
runtime. The classifier + audit overlay that *produces* spine records over the
``RunnerBackend`` provision/run/collect/teardown lifecycle is the deferred
G-1.3b slice.

A file is treated as a candidate Runtime Evidence chain when it satisfies all
of:

* YAML extension (``.yml`` / ``.yaml``);
* not under a ``schemas/`` or ``templates/`` directory;
* its path basename does NOT contain ``".tmp."``;
* the loaded YAML is a mapping whose ``kind`` field equals
  ``runtime-evidence-chain``.

Failures cite the offending error class and the prose contract at
``docs/contracts/runtime-evidence.md``.

This check is **defensive** — it makes the Creator Engine's own runtime audit
trail tamper-evident.

See:
  - ``docs/contracts/runtime-evidence.md``
  - ``schemas/runtime-evidence.schema.yaml``
  - ``creator_engine_validator/runtime_evidence_spine.py``
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..runtime_evidence_spine import CHAIN_KIND, verify_chain
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "ce_runtime_evidence"
CONTRACT = "docs/contracts/runtime-evidence.md"
SCHEMA = "schemas/runtime-evidence.schema.yaml"
KIND_VALUE = CHAIN_KIND

# Failure codes (explicit error classes, per the contract's predicate table).
CODE_SCHEMA = "runtime_evidence_schema_violation"
CODE_INVALID = "runtime_evidence_invalid_record"
CODE_CONTENT_ADDRESS = "runtime_evidence_content_address"
CODE_CHAIN_LINK = "runtime_evidence_chain_link"
CODE_SEQUENCE = "runtime_evidence_sequence_break"
CODE_POLICY_UNBOUND = "runtime_evidence_policy_unbound"

# Map the spine's semantic finding kinds to this check's stable error codes.
_FINDING_CODE = {
    "content_address": CODE_CONTENT_ADDRESS,
    "chain_link": CODE_CHAIN_LINK,
    "sequence": CODE_SEQUENCE,
    "policy_unbound": CODE_POLICY_UNBOUND,
}


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts or "templates" in parts


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _record_is_runtime_evidence_chain(record: Any) -> bool:
    return isinstance(record, dict) and record.get("kind") == KIND_VALUE


def iter_runtime_evidence_chains(paths: Iterable[Path]) -> list[Path]:
    """Return candidate Runtime Evidence chain files under ``paths``."""
    seen: set[Path] = set()
    records: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if _looks_like_yaml(path) and not _is_under_excluded(path) and not _is_tmp_artifact(path):
            candidates = [path]
        elif path.is_dir():
            candidates = [
                p
                for p in sorted(path.rglob("*.yml")) + sorted(path.rglob("*.yaml"))
                if _looks_like_yaml(p)
                and not _is_under_excluded(p)
                and not _is_tmp_artifact(p)
            ]
        else:
            candidates = []
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            try:
                data = load_yaml(candidate)
            except LoaderError:
                continue
            if not _record_is_runtime_evidence_chain(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def validate_runtime_evidence_chain(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one chain wrapper against the schema + tamper-evidence predicates."""
    errors: list[ValidationError] = []
    errors.extend(validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT))
    records = record.get("records")
    if not isinstance(records, list):
        # Schema validation owns a missing / mistyped records list.
        return errors
    for finding in verify_chain(records):
        errors.append(make_error(
            _FINDING_CODE.get(finding.kind, CODE_INVALID),
            path,
            f"records[{finding.index}]",
            finding.message,
            CONTRACT,
        ))
    return errors


@register(
    CHECK_NAME,
    [
        CODE_SCHEMA,
        CODE_INVALID,
        CODE_CONTENT_ADDRESS,
        CODE_CHAIN_LINK,
        CODE_SEQUENCE,
        CODE_POLICY_UNBOUND,
    ],
)
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for chain_path in iter_runtime_evidence_chains(paths):
        try:
            record = load_yaml(chain_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, chain_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(record, dict):
            errors.append(make_error(
                CODE_INVALID,
                chain_path,
                "/",
                "runtime-evidence chain must be a YAML mapping",
                CONTRACT,
            ))
            continue
        errors.extend(validate_runtime_evidence_chain(record, chain_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
