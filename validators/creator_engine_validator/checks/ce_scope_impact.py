"""Warning-only Scope impact propagation.

This check recomputes the canonical digest for ratified Scope records and surfaces
drift as non-blocking warnings. It is intentionally pure: no writes, subprocesses,
sockets, or v3 coordination imports.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from . import register

CHECK_NAME = "ce_scope_impact"
CONTRACT = "docs/contracts/scope.md"
KIND_VALUE = "scope-record"
RATIFIED_STATE = "ratified"
PLACEHOLDER = "__CE_SCOPE_RATIFICATION_PLACEHOLDER__"

CODE_SCOPE_CONTENT_DRIFT = "IMPACT-SCOPE-CONTENT-DRIFT"
CODE_DOWNSTREAM_AFFECTED = "IMPACT-DOWNSTREAM-AFFECTED"

_PLACEHOLDER_FIELDS = frozenset({"value", "ratified_scope_sha"})
_REF_FIELD_BY_KIND = {
    "plan": "path",
    "decision_record": "id",
    "test_pattern": "glob",
    "validator_check": "name",
    "scope": "scope_id",
}


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts or "templates" in parts


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _record_is_scope(record: Any) -> bool:
    return isinstance(record, dict) and record.get("kind") == KIND_VALUE


def _state_of(record: dict[str, Any]) -> str:
    state = record.get("state")
    return state if isinstance(state, str) else ""


def _is_ratified_scope(record: dict[str, Any]) -> bool:
    return _record_is_scope(record) and _state_of(record) == RATIFIED_STATE


def iter_scope_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate Scope record files under ``paths``."""
    seen: set[Path] = set()
    records: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if _looks_like_yaml(path) and not _is_under_excluded(path) and not _is_tmp_artifact(path):
            candidates = [path]
        elif path.is_dir():
            candidates = [
                p for p in sorted(path.rglob("*.yml")) + sorted(path.rglob("*.yaml"))
                if _looks_like_yaml(p) and not _is_under_excluded(p) and not _is_tmp_artifact(p)
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
            if not _record_is_scope(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def _placeholder_digest_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: PLACEHOLDER if key in _PLACEHOLDER_FIELDS else _placeholder_digest_fields(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_placeholder_digest_fields(item) for item in value]
    return value


def canonical_scope_bytes(scope: dict[str, Any]) -> bytes:
    canonical = _placeholder_digest_fields(scope)
    return json.dumps(canonical, sort_keys=True, ensure_ascii=True).encode("ascii")


def ratified_scope_sha(scope: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_scope_bytes(scope)).hexdigest()


def _declared_sha(scope: dict[str, Any]) -> str | None:
    ratification = scope.get("ratification")
    if not isinstance(ratification, dict):
        return None
    value = ratification.get("ratified_scope_sha")
    return value if isinstance(value, str) else None


def _downstream_refs(scope: dict[str, Any]) -> list[Any]:
    refs = scope.get("downstream_refs")
    return refs if isinstance(refs, list) else []


def _format_downstream_ref(ref: Any) -> str:
    if not isinstance(ref, dict):
        return json.dumps(ref, sort_keys=True, ensure_ascii=True)
    kind = ref.get("kind")
    field = _REF_FIELD_BY_KIND.get(kind)
    if isinstance(kind, str) and field and isinstance(ref.get(field), str):
        return f"{kind} {field}={ref[field]}"
    return json.dumps(ref, sort_keys=True, ensure_ascii=True)


def validate_scope_impact(scope: dict[str, Any], path: Path) -> list[ValidationError]:
    """Return warning records for one Scope. Errors are never produced."""
    if not _is_ratified_scope(scope):
        return []
    expected = _declared_sha(scope)
    if not expected:
        return []
    actual = ratified_scope_sha(scope)
    if actual == expected:
        return []

    warnings = [
        make_error(
            CODE_SCOPE_CONTENT_DRIFT,
            path,
            "ratification/ratified_scope_sha",
            f"ratified Scope content digest drifted: declared {expected}, recomputed {actual}",
            CONTRACT,
        )
    ]
    for index, ref in enumerate(_downstream_refs(scope)):
        warnings.append(
            make_error(
                CODE_DOWNSTREAM_AFFECTED,
                path,
                f"downstream_refs/{index}",
                f"ratified Scope content drift affects downstream artifact {_format_downstream_ref(ref)}",
                CONTRACT,
            )
        )
    return warnings


@register(CHECK_NAME, [CODE_SCOPE_CONTENT_DRIFT, CODE_DOWNSTREAM_AFFECTED])
def run(paths: Iterable[Path]) -> CheckResult:
    warnings: list[ValidationError] = []
    for record_path in iter_scope_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError:
            continue
        if not isinstance(record, dict):
            continue
        warnings.extend(validate_scope_impact(record, record_path))
    return CheckResult(name=CHECK_NAME, warnings=tuple(warnings))
