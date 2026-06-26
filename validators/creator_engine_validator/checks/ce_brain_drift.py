"""Knowledge-SSOT drift checker for active brain assertions.

This check re-verifies the current active assertion view against each
assertion's ``evidence_ref``. Probe-backed assertions use the live probe seam;
local artifact assertions fail closed when their evidence cannot be resolved.
Workflow/config artifacts are deliberately checked through semantic projections
or probes instead of raw full-file hashes, so unrelated edit churn does not
create false drift.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import yaml

from .. import brain_probe
from .. import brain_runtime
from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from . import register
from .ce_brain_assertions import iter_brain_assertion_files

CHECK_NAME = "ce_brain_drift"
CONTRACT = brain_runtime.CONTRACT
AUTHORITATIVE_LEDGER_RELATIVE_PATH = Path(".ce") / "brain" / "assertions.yaml"

CODE_DRIFT = "brain_assertion_drift"
CODE_UNVERIFIABLE = "brain_assertion_unverifiable"
CODE_AUTHORITATIVE_MISMATCH = "brain_assertion_authoritative_mismatch"

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
_PROJECTION_CLAIM_KEYS = (
    "projection",
    "normalized_projection",
    "semantic_projection",
)
_SUPPORTED_COMPARISON_KEYS = frozenset((*_HASH_CLAIM_KEYS, *_VALUE_CLAIM_KEYS))
_HASH_LIKE_KEY_TOKENS = ("sha", "hash", "digest", "checksum")
_VOLATILE_WORKFLOW_CONFIG_DIRS = (
    (".github", "workflows"),
)
_FULL_ARTIFACT_ANCHOR_KEYS = frozenset((*_HASH_CLAIM_KEYS, *_VALUE_CLAIM_KEYS))
_MISSING = object()


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
class DriftFinding(ValidationError):
    assertion_id: str
    claimed: str
    observed: str
    evidence_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "path": self.path,
            "message": self.message,
            "contract": self.contract,
            "assertion_id": self.assertion_id,
            "claimed": self.claimed,
            "observed": self.observed,
        }
        if self.evidence_ref is not None:
            payload["evidence_ref"] = self.evidence_ref
        return payload


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


def _drift_error(
    path: Path,
    pointer_prefix: tuple[Any, ...],
    field: str,
    message: str,
    *,
    assertion_id: str,
    claimed: str,
    observed: str,
    evidence_ref: str | None = None,
) -> DriftFinding:
    rendered_path = f"{path}:{_pointer(pointer_prefix + (field,))}"
    return DriftFinding(
        code=CODE_DRIFT,
        path=rendered_path,
        message=message,
        contract=CONTRACT,
        assertion_id=assertion_id,
        claimed=claimed,
        observed=observed,
        evidence_ref=evidence_ref,
    )


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


def _raw_projection_specs(claim: Mapping[str, Any]) -> list[tuple[str, Any]]:
    out: list[tuple[str, Any]] = []
    for key in _PROJECTION_CLAIM_KEYS:
        if key in claim:
            out.append((key, claim[key]))
    evidence = claim.get("evidence")
    if isinstance(evidence, Mapping):
        for key in _PROJECTION_CLAIM_KEYS:
            if key in evidence:
                out.append((f"evidence.{key}", evidence[key]))
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
    if token in _SUPPORTED_COMPARISON_KEYS or token in _PROJECTION_CLAIM_KEYS:
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


def _artifact_relative_parts(artifact: Path, context: DriftContext) -> tuple[str, ...]:
    try:
        relative = artifact.resolve().relative_to(context.root().resolve())
    except (OSError, ValueError):
        return artifact.parts
    return relative.parts


def _is_volatile_workflow_config_artifact(artifact: Path, context: DriftContext) -> bool:
    parts = _artifact_relative_parts(artifact, context)
    normalized = tuple(str(part) for part in parts)
    return any(
        len(normalized) >= len(prefix) + 1
        and normalized[: len(prefix)] == prefix
        and artifact.suffix.lower() in {".yml", ".yaml"}
        for prefix in _VOLATILE_WORKFLOW_CONFIG_DIRS
    )


def _full_artifact_anchor_keys(claim: Mapping[str, Any]) -> list[str]:
    keys = [key for key in _FULL_ARTIFACT_ANCHOR_KEYS if key in claim]
    evidence = claim.get("evidence")
    if isinstance(evidence, Mapping):
        keys.extend(f"evidence.{key}" for key in _FULL_ARTIFACT_ANCHOR_KEYS if key in evidence)
    return sorted(keys)


def _is_workflow_claim(claim: Mapping[str, Any]) -> bool:
    return claim.get("subject") == "workflow"


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _projection_specs(
    claim: Mapping[str, Any],
    path: Path,
    pointer_prefix: tuple[Any, ...],
    assertion_id: str,
) -> tuple[list[tuple[str, Mapping[str, Any]]], list[ValidationError]]:
    specs: list[tuple[str, Mapping[str, Any]]] = []
    errors: list[ValidationError] = []
    for key, raw in _raw_projection_specs(claim):
        raw_specs = raw if isinstance(raw, list) else [raw]
        if not isinstance(raw, (Mapping, list)):
            errors.append(
                _error(
                    CODE_UNVERIFIABLE,
                    path,
                    pointer_prefix,
                    "claim",
                    f"assertion {assertion_id}: claim.{key} must be a projection mapping or list of mappings",
                )
            )
            continue
        for idx, spec in enumerate(raw_specs):
            label = key if not isinstance(raw, list) else f"{key}[{idx}]"
            if not isinstance(spec, Mapping):
                errors.append(
                    _error(
                        CODE_UNVERIFIABLE,
                        path,
                        pointer_prefix,
                        "claim",
                        f"assertion {assertion_id}: claim.{label} must be a projection mapping",
                    )
                )
                continue
            specs.append((label, spec))
    return specs, errors


def _yaml_projection_path(spec: Mapping[str, Any]) -> Sequence[Any] | None:
    raw_path = spec.get("path")
    if isinstance(raw_path, str) and raw_path:
        return tuple(part for part in raw_path.split(".") if part)
    if isinstance(raw_path, list) and all(isinstance(part, (str, int)) for part in raw_path):
        return tuple(raw_path)
    return None


def _mapping_get(value: Mapping[Any, Any], key: Any) -> Any:
    if key in value:
        return value[key]
    if key == "on" and True in value:
        return value[True]
    return _MISSING


def _select_yaml_path(document: Any, parts: Sequence[Any]) -> Any:
    current = document
    for part in parts:
        if isinstance(current, Mapping):
            current = _mapping_get(current, part)
        elif isinstance(current, list) and isinstance(part, int) and not isinstance(part, bool):
            current = current[part] if 0 <= part < len(current) else _MISSING
        else:
            return _MISSING
        if current is _MISSING:
            return _MISSING
    return current


def _as_string_set(value: Any) -> list[str]:
    values = value if isinstance(value, list) else [value]
    return sorted({str(item) for item in values})


def _projection_verdict(
    *,
    document: Any,
    spec: Mapping[str, Any],
) -> tuple[bool, str, str, str | None]:
    spec_type = spec.get("type", "yaml-path")
    if spec_type not in {"yaml-path", "yaml_path"}:
        return False, "", "", f"projection.type must be 'yaml-path', got {spec_type!r}"
    parts = _yaml_projection_path(spec)
    if parts is None:
        return False, "", "", "projection.path must be a dotted string or list of string/int path parts"
    if "expected" not in spec:
        return False, "", "", "projection.expected is required"
    normalize = spec.get("normalize", "json")
    observed_raw = _select_yaml_path(document, parts)
    expected_raw = spec["expected"]
    if normalize == "presence":
        observed = observed_raw is not _MISSING
        expected = bool(expected_raw)
        return observed == expected, f"presence={expected}", f"presence={observed}", None
    if observed_raw is _MISSING:
        return False, _stable_json(expected_raw), "<missing>", None
    if normalize == "string_set":
        observed_set = _as_string_set(observed_raw)
        expected_set = _as_string_set(expected_raw)
        return observed_set == expected_set, f"strings={_stable_json(expected_set)}", f"strings={_stable_json(observed_set)}", None
    if normalize == "string_set_contains":
        observed_set = _as_string_set(observed_raw)
        expected_set = _as_string_set(expected_raw)
        ok = set(expected_set).issubset(observed_set)
        return ok, f"contains={_stable_json(expected_set)}", f"strings={_stable_json(observed_set)}", None
    if normalize == "string":
        observed = str(observed_raw)
        expected = str(expected_raw)
        return observed == expected, f"string={expected!r}", f"string={observed!r}", None
    if normalize == "json":
        observed = _stable_json(observed_raw)
        expected = _stable_json(expected_raw)
        return observed == expected, f"json={expected}", f"json={observed}", None
    return False, "", "", f"projection.normalize {normalize!r} is not supported"


def _verify_projection_claims(
    *,
    data: bytes,
    specs: list[tuple[str, Mapping[str, Any]]],
    path: Path,
    pointer_prefix: tuple[Any, ...],
    assertion_id: str,
    evidence_ref: str,
) -> list[ValidationError]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [
            _error(
                CODE_UNVERIFIABLE,
                path,
                pointer_prefix,
                "evidence_ref",
                f"assertion {assertion_id}: evidence_ref {evidence_ref!r} is not UTF-8 ({exc.__class__.__name__})",
            )
        ]
    try:
        document = yaml.safe_load(text)
    except Exception as exc:
        return [
            _error(
                CODE_UNVERIFIABLE,
                path,
                pointer_prefix,
                "evidence_ref",
                f"assertion {assertion_id}: evidence_ref {evidence_ref!r} is not parseable YAML ({exc.__class__.__name__})",
            )
        ]
    findings: list[ValidationError] = []
    for key, spec in specs:
        ok, claimed, observed, error = _projection_verdict(document=document, spec=spec)
        if error is not None:
            findings.append(
                _error(
                    CODE_UNVERIFIABLE,
                    path,
                    pointer_prefix,
                    "claim",
                    f"assertion {assertion_id}: claim.{key} {error}",
                )
            )
            continue
        if ok:
            continue
        findings.append(
            _drift_error(
                path,
                pointer_prefix,
                "claim",
                (
                    f"assertion {assertion_id}: artifact projection drifted for claim.{key}; "
                    f"claimed {claimed}, observed {observed}"
                ),
                assertion_id=assertion_id,
                claimed=claimed,
                observed=observed,
                evidence_ref=evidence_ref,
            )
        )
    return findings


def _repo_root_from_state_root(state_root: Path | str) -> Path:
    root = Path(state_root)
    if root.name == "state" and root.parent.name == ".ce":
        return root.parent.parent
    return Path(".")


def _repo_root_for_repo_local_state_root(state_root: Path | str) -> Path | None:
    root = Path(state_root)
    if root.name == "state" and root.parent.name == ".ce":
        return root.parent.parent
    return None


def _drift_ledger_path(state_root: Path | str) -> Path:
    state_ledger = brain_runtime.ledger_path(state_root)
    if state_ledger.is_file():
        return state_ledger
    repo_root = _repo_root_for_repo_local_state_root(state_root)
    if repo_root is None:
        return state_ledger
    authoritative = repo_root / AUTHORITATIVE_LEDGER_RELATIVE_PATH
    return authoritative if authoritative.is_file() else state_ledger


def _repo_root_from_ledger_path(path: Path) -> Path:
    parts = path.parts
    for idx, part in enumerate(parts):
        if part == ".ce":
            return Path(*parts[:idx]) if idx > 0 else Path(".")
    return Path(".")


def _is_loaded_runtime_ledger(path: Path) -> bool:
    return (
        path.name == "assertions.yaml"
        and path.parent.name == "brain"
        and path.parent.parent.name == "state"
        and path.parent.parent.parent.name == ".ce"
    )


def _authoritative_mismatch_errors(path: Path, context: DriftContext) -> list[ValidationError]:
    authoritative_path = brain_runtime.authoritative_ledger_path(context.root())
    if not authoritative_path.is_file() or not path.is_file():
        return []
    try:
        runtime_records = brain_runtime.load_records_from_path(path)
        authoritative_records = brain_runtime.load_records_from_path(authoritative_path)
    except brain_runtime.BrainLedgerInvalid:
        return []
    if runtime_records == authoritative_records:
        return []
    runtime_head = (
        str(runtime_records[-1].get("content_hash"))
        if runtime_records and isinstance(runtime_records[-1].get("content_hash"), str)
        else "<none>"
    )
    authoritative_head = (
        str(authoritative_records[-1].get("content_hash"))
        if authoritative_records and isinstance(authoritative_records[-1].get("content_hash"), str)
        else "<none>"
    )
    return [
        make_error(
            CODE_AUTHORITATIVE_MISMATCH,
            path,
            "/",
            (
                "loaded brain assertion ledger diverges from authoritative store "
                f"{authoritative_path}; loaded head={runtime_head}, authoritative head={authoritative_head}"
            ),
            CONTRACT,
        )
    ]


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
    if observed.verdict == "unknown" and expected != "unknown":
        return [
            _error(
                CODE_UNVERIFIABLE,
                path,
                pointer_prefix,
                "claim",
                (
                    f"assertion {assertion_id}: probe {probe_name!r} is unverifiable; "
                    f"claimed verdict={expected!r}, observed verdict='unknown'"
                ),
            )
        ]
    if observed.verdict == expected:
        return []
    return [
        _drift_error(
            path,
            pointer_prefix,
            "claim",
            (
                f"assertion {assertion_id}: probe {probe_name!r} drifted; "
                f"claimed verdict={expected!r}, observed verdict={observed.verdict!r}"
            ),
            assertion_id=assertion_id,
            claimed=f"verdict={expected}",
            observed=f"verdict={observed.verdict}",
            evidence_ref=str(record.get("evidence_ref")),
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
    claimed_projections, projection_errors = _projection_specs(claim, path, pointer_prefix, assertion_id)
    comparison_errors.extend(projection_errors)
    if comparison_errors:
        return comparison_errors

    claimed_hashes = _claimed_hashes(claim)
    claimed_values = _claimed_values(claim)
    if _is_workflow_claim(claim) and _is_volatile_workflow_config_artifact(artifact, context):
        unstable_keys = _full_artifact_anchor_keys(claim)
        if unstable_keys:
            return [
                _error(
                    CODE_UNVERIFIABLE,
                    path,
                    pointer_prefix,
                    "claim",
                    (
                        f"assertion {assertion_id}: workflow/config evidence {evidence_ref!r} "
                        f"must not use full-artifact hash/value anchors ({', '.join(unstable_keys)}); "
                        "use a probe, normalized projection, or stable contract artifact instead"
                    ),
                )
            ]
    if not claimed_hashes and not claimed_values and not claimed_projections:
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
    if claimed_projections:
        findings.extend(
            _verify_projection_claims(
                data=data,
                specs=claimed_projections,
                path=path,
                pointer_prefix=pointer_prefix,
                assertion_id=assertion_id,
                evidence_ref=evidence_ref,
            )
        )
    observed_hash = hashlib.sha256(data).hexdigest()
    for key, claimed_hash in claimed_hashes:
        if claimed_hash == observed_hash:
            continue
        findings.append(
            _drift_error(
                path,
                pointer_prefix,
                "claim",
                (
                    f"assertion {assertion_id}: artifact hash drifted for claim.{key}; "
                    f"claimed sha256={claimed_hash}, observed sha256={observed_hash}"
                ),
                assertion_id=assertion_id,
                claimed=f"sha256={claimed_hash}",
                observed=f"sha256={observed_hash}",
                evidence_ref=evidence_ref,
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
                _drift_error(
                    path,
                    pointer_prefix,
                    "claim",
                    (
                        f"assertion {assertion_id}: artifact value drifted for claim.{key}; "
                        f"claimed value={claimed_value!r}, observed value={observed_value!r}"
                    ),
                    assertion_id=assertion_id,
                    claimed=f"value={claimed_value!r}",
                    observed=f"value={observed_value!r}",
                    evidence_ref=evidence_ref,
                )
            )
    return findings


def _verify_record(record: Mapping[str, Any], path: Path, pointer_prefix: tuple[Any, ...], context: DriftContext) -> list[ValidationError]:
    verification_method = record.get("verification_method")
    if isinstance(verification_method, Mapping):
        method_type = verification_method.get("type")
    elif isinstance(verification_method, str):
        method_type = verification_method
    else:
        method_type = None
    if method_type == "manual-attested":
        return []
    if method_type == "static":
        return _verify_artifact_record(record, path, pointer_prefix, context)
    if method_type == "probe" or brain_probe.record_probe_name(record) is not None:
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
    path = _drift_ledger_path(state_root)
    if context is None:
        repo_root = _repo_root_from_state_root(state_root)
        context = DriftContext(
            repo_root=repo_root,
            probe_context=brain_probe.ProbeContext(repo_root=repo_root),
        )
    findings_list: list[ValidationError] = []
    if path.is_file():
        findings_list.extend(validate_file(path, context=context))
        if _is_loaded_runtime_ledger(path):
            findings_list.extend(_authoritative_mismatch_errors(path, context))
    findings = tuple(findings_list)
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


@register(CHECK_NAME, [CODE_DRIFT, CODE_UNVERIFIABLE, CODE_AUTHORITATIVE_MISMATCH])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    checked_mismatch_paths: set[Path] = set()
    for path in iter_brain_assertion_files(paths):
        repo_root = _repo_root_from_ledger_path(path)
        context = DriftContext(
            repo_root=repo_root,
            probe_context=brain_probe.ProbeContext(repo_root=repo_root),
        )
        errors.extend(validate_file(path, context=context))
        if not _is_loaded_runtime_ledger(path):
            continue
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        if resolved in checked_mismatch_paths:
            continue
        checked_mismatch_paths.add(resolved)
        errors.extend(_authoritative_mismatch_errors(path, context))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
