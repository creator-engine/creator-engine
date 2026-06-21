"""Knowledge-SSOT drift checker for active brain assertions.

This check re-verifies the current active assertion view against each
assertion's ``evidence_ref``. Probe-backed assertions use the live probe seam;
local artifact assertions fail closed when their evidence cannot be resolved.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from .. import brain_probe
from .. import brain_runtime
from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from . import register
from .ce_brain_assertions import iter_brain_assertion_files

CHECK_NAME = "ce_brain_drift"
CONTRACT = brain_runtime.CONTRACT

CODE_DRIFT = "brain_assertion_drift"
CODE_UNVERIFIABLE = "brain_assertion_unverifiable"

_HASH_RE = re.compile(r"^(?:sha256:)?([0-9a-f]{64})$")
_HASH_CLAIM_KEYS = (
    "sha256",
    "content_hash",
    "content_sha256",
    "evidence_sha256",
    "artifact_sha256",
    "source_sha256",
)
_VALUE_CLAIM_KEYS = (
    "value",
    "expected_value",
    "evidence_value",
    "artifact_value",
    "content_value",
)
_SUPPORTED_COMPARISON_KEYS = frozenset((*_HASH_CLAIM_KEYS, *_VALUE_CLAIM_KEYS))
_HASH_LIKE_KEY_TOKENS = ("sha", "hash", "digest", "checksum")


def _default_read_bytes(path: Path) -> bytes:  # pragma: no cover - live edge
    return path.read_bytes()


@dataclass(frozen=True)
class DriftContext:
    repo_root: Path | str = Path(".")
    probe_context: brain_probe.ProbeContext | None = None
    read_bytes: Callable[[Path], bytes] = _default_read_bytes

    def root(self) -> Path:
        return Path(self.repo_root)


@dataclass(frozen=True)
class DriftResult:
    ok: bool
    ledger_path: Path
    record_count: int
    active_count: int
    head_content_hash: str | None
    findings: tuple[ValidationError, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_count": self.active_count,
            "findings": [finding.to_dict() for finding in self.findings],
            "head_content_hash": self.head_content_hash,
            "ledger_path": str(self.ledger_path),
            "ok": self.ok,
            "record_count": self.record_count,
        }


def _pointer(parts: tuple[Any, ...]) -> str:
    rendered = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(rendered) if rendered else "/"


def _error(
    code: str,
    path: Path,
    pointer_prefix: tuple[Any, ...],
    field: str,
    message: str,
) -> ValidationError:
    return make_error(code, path, _pointer(pointer_prefix + (field,)), message, CONTRACT)


def _active_record_indexes(records: list[Any]) -> list[int]:
    latest: dict[str, int] = {}
    for idx, record in enumerate(records):
        if isinstance(record, dict) and isinstance(record.get("id"), str):
            latest[record["id"]] = idx
    return sorted(
        idx
        for idx in latest.values()
        if isinstance(records[idx], dict) and records[idx].get("status") == "active"
    )


def _normalize_claimed_hash(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    match = _HASH_RE.match(value.strip().lower())
    return match.group(1) if match else None


def _claimed_hashes(claim: Mapping[str, Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for key in _HASH_CLAIM_KEYS:
        digest = _normalize_claimed_hash(claim.get(key))
        if digest is not None:
            out.append((key, digest))
    evidence = claim.get("evidence")
    if isinstance(evidence, Mapping):
        for key in _HASH_CLAIM_KEYS:
            digest = _normalize_claimed_hash(evidence.get(key))
            if digest is not None:
                out.append((f"evidence.{key}", digest))
    return out


def _claimed_values(claim: Mapping[str, Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for key in _VALUE_CLAIM_KEYS:
        value = claim.get(key)
        if isinstance(value, str):
            out.append((key, value))
    evidence = claim.get("evidence")
    if isinstance(evidence, Mapping):
        for key in _VALUE_CLAIM_KEYS:
            value = evidence.get(key)
            if isinstance(value, str):
                out.append((f"evidence.{key}", value))
    return out


def _comparison_malformed_errors(claim: Mapping[str, Any], path: Path, pointer_prefix: tuple[Any, ...], assertion_id: str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for key in _HASH_CLAIM_KEYS:
        if key in claim and _normalize_claimed_hash(claim.get(key)) is None:
            errors.append(
                _error(
                    CODE_UNVERIFIABLE,
                    path,
                    pointer_prefix,
                    "claim",
                    f"assertion {assertion_id}: claim.{key} must be a sha256 hex string",
                )
            )
    for key in _VALUE_CLAIM_KEYS:
        if key in claim and not isinstance(claim.get(key), str):
            errors.append(
                _error(
                    CODE_UNVERIFIABLE,
                    path,
                    pointer_prefix,
                    "claim",
                    f"assertion {assertion_id}: claim.{key} must be a string value",
                )
            )
    evidence = claim.get("evidence")
    if isinstance(evidence, Mapping):
        for key in _HASH_CLAIM_KEYS:
            if key in evidence and _normalize_claimed_hash(evidence.get(key)) is None:
                errors.append(
                    _error(
                        CODE_UNVERIFIABLE,
                        path,
                        pointer_prefix,
                        "claim",
                        f"assertion {assertion_id}: claim.evidence.{key} must be a sha256 hex string",
                    )
                )
        for key in _VALUE_CLAIM_KEYS:
            if key in evidence and not isinstance(evidence.get(key), str):
                errors.append(
                    _error(
                        CODE_UNVERIFIABLE,
                        path,
                        pointer_prefix,
                        "claim",
                        f"assertion {assertion_id}: claim.evidence.{key} must be a string value",
                    )
                )
    return errors


def _looks_like_unsupported_comparison_key(key: Any) -> bool:
    token = str(key).strip().lower().replace("-", "_")
    if token in _SUPPORTED_COMPARISON_KEYS:
        return False
    return any(part in token for part in _HASH_LIKE_KEY_TOKENS) or token.endswith("_value")


def _comparison_unsupported_errors(claim: Mapping[str, Any], path: Path, pointer_prefix: tuple[Any, ...], assertion_id: str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for key in claim:
        if _looks_like_unsupported_comparison_key(key):
            errors.append(
                _error(
                    CODE_UNVERIFIABLE,
                    path,
                    pointer_prefix,
                    "claim",
                    (
                        f"assertion {assertion_id}: claim.{key} is not a supported drift comparison key; "
                        f"supported hash keys={sorted(_HASH_CLAIM_KEYS)}, supported value keys={sorted(_VALUE_CLAIM_KEYS)}"
                    ),
                )
            )
    evidence = claim.get("evidence")
    if isinstance(evidence, Mapping):
        for key in evidence:
            if _looks_like_unsupported_comparison_key(key):
                errors.append(
                    _error(
                        CODE_UNVERIFIABLE,
                        path,
                        pointer_prefix,
                        "claim",
                        (
                            f"assertion {assertion_id}: claim.evidence.{key} is not a supported drift comparison key; "
                            f"supported hash keys={sorted(_HASH_CLAIM_KEYS)}, supported value keys={sorted(_VALUE_CLAIM_KEYS)}"
                        ),
                    )
                )
    return errors


def _resolve_artifact(evidence_ref: str, context: DriftContext) -> Path | None:
    path_part = evidence_ref.split("#", 1)[0]
    if not path_part:
        return None
    candidate = Path(path_part)
    if not candidate.is_absolute():
        candidate = context.root() / candidate
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    return resolved if resolved.is_file() else None


def _verify_probe_record(record: Mapping[str, Any], path: Path, pointer_prefix: tuple[Any, ...], context: DriftContext) -> list[ValidationError]:
    probe_name = brain_probe.record_probe_name(record)
    if probe_name is None:
        return []
    assertion_id = str(record.get("id"))
    expected = brain_probe.record_expected_verdict(record)
    if expected is None:
        return [
            _error(
                CODE_UNVERIFIABLE,
                path,
                pointer_prefix,
                "claim",
                (
                    f"assertion {assertion_id}: probe evidence {probe_name!r} is unverifiable "
                    "without claim.verdict present|absent|unknown"
                ),
            )
        ]
    observed = brain_probe.probe(probe_name, context.probe_context)
    if observed.verdict == expected:
        return []
    return [
        _error(
            CODE_DRIFT,
            path,
            pointer_prefix,
            "claim",
            (
                f"assertion {assertion_id}: probe {probe_name!r} drifted; "
                f"claimed verdict={expected!r}, observed verdict={observed.verdict!r}"
            ),
        )
    ]


def _verify_artifact_record(record: Mapping[str, Any], path: Path, pointer_prefix: tuple[Any, ...], context: DriftContext) -> list[ValidationError]:
    assertion_id = str(record.get("id"))
    evidence_ref = record.get("evidence_ref")
    if not isinstance(evidence_ref, str) or not evidence_ref:
        return [
            _error(
                CODE_UNVERIFIABLE,
                path,
                pointer_prefix,
                "evidence_ref",
                f"assertion {assertion_id}: evidence_ref is missing or not a string",
            )
        ]
    artifact = _resolve_artifact(evidence_ref, context)
    if artifact is None:
        return [
            _error(
                CODE_UNVERIFIABLE,
                path,
                pointer_prefix,
                "evidence_ref",
                f"assertion {assertion_id}: evidence_ref {evidence_ref!r} is not a resolvable local file",
            )
        ]
    try:
        data = context.read_bytes(artifact)
    except Exception as exc:
        return [
            _error(
                CODE_UNVERIFIABLE,
                path,
                pointer_prefix,
                "evidence_ref",
                f"assertion {assertion_id}: evidence_ref {evidence_ref!r} could not be read ({exc.__class__.__name__})",
            )
        ]

    claim = record.get("claim")
    if not isinstance(claim, Mapping):
        return [
            _error(
                CODE_UNVERIFIABLE,
                path,
                pointer_prefix,
                "claim",
                f"assertion {assertion_id}: claim is not a mapping",
            )
        ]

    comparison_errors = [
        *_comparison_malformed_errors(claim, path, pointer_prefix, assertion_id),
        *_comparison_unsupported_errors(claim, path, pointer_prefix, assertion_id),
    ]
    if comparison_errors:
        return comparison_errors

    claimed_hashes = _claimed_hashes(claim)
    claimed_values = _claimed_values(claim)
    if not claimed_hashes and not claimed_values:
        return [
            _error(
                CODE_UNVERIFIABLE,
                path,
                pointer_prefix,
                "claim",
                (
                    f"assertion {assertion_id}: artifact evidence requires an explicit supported "
                    "hash or value claim; evidence file existence alone is not verification"
                ),
            )
        ]

    findings: list[ValidationError] = []
    observed_hash = hashlib.sha256(data).hexdigest()
    for key, claimed_hash in claimed_hashes:
        if claimed_hash == observed_hash:
            continue
        findings.append(
            _error(
                CODE_DRIFT,
                path,
                pointer_prefix,
                "claim",
                (
                    f"assertion {assertion_id}: artifact hash drifted for claim.{key}; "
                    f"claimed sha256={claimed_hash}, observed sha256={observed_hash}"
                ),
            )
        )

    if claimed_values:
        try:
            observed_value = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            findings.append(
                _error(
                    CODE_UNVERIFIABLE,
                    path,
                    pointer_prefix,
                    "evidence_ref",
                    (
                        f"assertion {assertion_id}: evidence_ref {evidence_ref!r} is not UTF-8 "
                        f"but declares value claims ({exc.__class__.__name__})"
                    ),
                )
            )
            return findings
        for key, claimed_value in claimed_values:
            if claimed_value == observed_value:
                continue
            findings.append(
                _error(
                    CODE_DRIFT,
                    path,
                    pointer_prefix,
                    "claim",
                    (
                        f"assertion {assertion_id}: artifact value drifted for claim.{key}; "
                        f"claimed value={claimed_value!r}, observed value={observed_value!r}"
                    ),
                )
            )
    return findings


def _verify_record(record: Mapping[str, Any], path: Path, pointer_prefix: tuple[Any, ...], context: DriftContext) -> list[ValidationError]:
    if brain_probe.record_probe_name(record) is not None:
        return _verify_probe_record(record, path, pointer_prefix, context)
    return _verify_artifact_record(record, path, pointer_prefix, context)


def validate_file(path: Path, *, context: DriftContext | None = None) -> list[ValidationError]:
    ctx = context or DriftContext()
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
        record = data["brain_assertion"]
        if isinstance(record, Mapping) and record.get("status") == "active":
            return _verify_record(record, path, ("brain_assertion",), ctx)
        return []

    errors = brain_runtime.validate_ledger_doc(data, path)
    if errors:
        return errors
    records = data.get("records")
    if not isinstance(records, list):
        return []
    findings: list[ValidationError] = []
    for idx in _active_record_indexes(records):
        record = records[idx]
        if isinstance(record, Mapping):
            findings.extend(_verify_record(record, path, ("records", idx), ctx))
    return findings


def verify_state_root(state_root: Path | str, *, context: DriftContext | None = None) -> DriftResult:
    path = brain_runtime.ledger_path(state_root)
    findings = tuple(validate_file(path, context=context)) if path.is_file() else ()
    record_count = 0
    active_count = 0
    head_content_hash: str | None = None
    if path.is_file():
        try:
            data = load_yaml(path)
        except LoaderError:
            data = None
        records = data.get("records") if isinstance(data, dict) and isinstance(data.get("records"), list) else []
        record_count = len(records)
        active_count = len(_active_record_indexes(records))
        head = records[-1] if records and isinstance(records[-1], Mapping) else None
        if head is not None and isinstance(head.get("content_hash"), str):
            head_content_hash = head["content_hash"]
    return DriftResult(
        ok=not findings,
        ledger_path=path,
        record_count=record_count,
        active_count=active_count,
        head_content_hash=head_content_hash,
        findings=findings,
    )


@register(CHECK_NAME, [CODE_DRIFT, CODE_UNVERIFIABLE])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for path in iter_brain_assertion_files(paths):
        errors.extend(validate_file(path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
