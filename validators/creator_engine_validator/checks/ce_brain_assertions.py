"""Knowledge-SSOT brain assertion ledger validator.

This check validates static ``brain-assertion-ledger`` YAML files for schema
conformance, deterministic content hashes, chain linkage, supersession
integrity, and fail-closed duplicate active claims.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from .. import brain_probe
from .. import brain_runtime
from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from . import register

CHECK_NAME = "ce_brain_assertions"
CONTRACT = brain_runtime.CONTRACT


def _pointer(parts: tuple[Any, ...]) -> str:
    rendered = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(rendered) if rendered else "/"


def _is_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in {".yml", ".yaml"}


def _is_excluded(path: Path) -> bool:
    return (
        ".tmp." in path.name
        or "schemas" in path.parts
        or "templates" in path.parts
        or "wheelhouse" in path.parts
        or "__pycache__" in path.parts
    )


def _is_brain_doc(data: Any) -> bool:
    return isinstance(data, dict) and (
        data.get("kind") == brain_runtime.LEDGER_KIND or "brain_assertion" in data
    )


def _looks_like_brain_ledger_path(path: Path) -> bool:
    return path.name in {"assertions.yml", "assertions.yaml"} and "brain" in path.parts


def iter_brain_assertion_files(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if _is_yaml(path) and not _is_excluded(path):
            candidates = [path]
        elif path.is_dir():
            candidates = [p for p in sorted(path.rglob("*.yml")) + sorted(path.rglob("*.yaml")) if _is_yaml(p) and not _is_excluded(p)]
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
                if _looks_like_brain_ledger_path(candidate):
                    seen.add(resolved)
                    out.append(candidate)
                continue
            if not (_looks_like_brain_ledger_path(candidate) or _is_brain_doc(data)):
                continue
            seen.add(resolved)
            out.append(candidate)
    return out


def _latest_active_indexes(records: list[Any]) -> dict[str, int]:
    latest: dict[str, int] = {}
    for idx, record in enumerate(records):
        if isinstance(record, dict) and isinstance(record.get("id"), str):
            latest[record["id"]] = idx
    return {
        rid: idx
        for rid, idx in latest.items()
        if isinstance(records[idx], dict) and records[idx].get("status") == "active"
    }


def _probe_backed_assertion_errors(
    records: list[Any],
    *,
    path: Path,
    pointer_prefix: tuple[Any, ...],
    include_index: bool,
    probe_context: brain_probe.ProbeContext | None,
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    active_indexes = _latest_active_indexes(records)
    for idx in active_indexes.values():
        record = records[idx]
        if not isinstance(record, dict):
            continue
        probe_name = brain_probe.record_probe_name(record)
        if probe_name is None:
            continue
        expected = brain_probe.record_expected_verdict(record)
        if expected is None:
            errors.append(
                make_error(
                    brain_probe.CODE_PROBE_EXPECTED_VERDICT,
                    path,
                    _pointer(
                        pointer_prefix + ((idx,) if include_index else ()) + ("claim", "verdict")
                    ),
                    (
                        f"probe-backed brain assertion for probe {probe_name!r} must declare "
                        "claim.verdict as one of 'present', 'absent', or 'unknown'"
                    ),
                    CONTRACT,
                )
            )
            continue
        observed = brain_probe.probe(probe_name, probe_context)
        if observed.verdict == expected:
            continue
        errors.append(
            make_error(
                brain_probe.CODE_PROBE_DISAGREEMENT,
                path,
                _pointer(
                    pointer_prefix + ((idx,) if include_index else ()) + ("claim", "verdict")
                ),
                (
                    f"probe-backed brain assertion verdict mismatch for probe {probe_name!r}: "
                    f"claim.verdict is {expected!r} but current probe verdict is {observed.verdict!r}"
                ),
                CONTRACT,
            )
        )
    return errors


def validate_file(path: Path, *, probe_context: brain_probe.ProbeContext | None = None) -> list[ValidationError]:
    try:
        data = load_yaml(path)
    except LoaderError as exc:
        return [make_error(brain_runtime.CODE_SCHEMA, path, "/", str(exc), CONTRACT)]
    if not isinstance(data, dict):
        return [make_error(brain_runtime.CODE_SCHEMA, path, "/", "brain assertion file must be a YAML mapping", CONTRACT)]
    if "brain_assertion" in data:
        doc = {
            "kind": brain_runtime.LEDGER_KIND,
            "record_type": brain_runtime.LEDGER_RECORD_TYPE,
            "schema_version": brain_runtime.SCHEMA_VERSION,
            "records": [data["brain_assertion"]],
        }
        errors = brain_runtime.validate_ledger_doc(doc, path)
        if errors:
            return errors
        return _probe_backed_assertion_errors(
            doc["records"],
            path=path,
            pointer_prefix=("brain_assertion",),
            include_index=False,
            probe_context=probe_context,
        )
    errors = brain_runtime.validate_ledger_doc(data, path)
    if errors:
        return errors
    records = data.get("records")
    if not isinstance(records, list):
        return []
    return _probe_backed_assertion_errors(
        records,
        path=path,
        pointer_prefix=("records",),
        include_index=True,
        probe_context=probe_context,
    )


@register(
    CHECK_NAME,
    [
        brain_runtime.CODE_SCHEMA,
        brain_runtime.CODE_CONTENT_ADDRESS,
        brain_runtime.CODE_CHAIN_LINK,
        brain_runtime.CODE_SEQUENCE,
        brain_runtime.CODE_FORBIDDEN_IDENTIFIER,
        brain_runtime.CODE_SUPERSEDE_TARGET,
        brain_runtime.CODE_DUPLICATE_ACTIVE,
        brain_probe.CODE_PROBE_EXPECTED_VERDICT,
        brain_probe.CODE_PROBE_DISAGREEMENT,
    ],
)
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for path in iter_brain_assertion_files(paths):
        errors.extend(validate_file(path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
