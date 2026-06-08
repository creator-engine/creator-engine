"""Scope record validation (v3 G-6 coordination layer).

Validates Scope records (`kind: scope-record`) against `schemas/scope.schema.yaml`
plus the cross-field coordination predicates: Definition-of-Ready completeness for
ready-or-later Scopes, appetite derivability (the G-5 appetite→spend-cap join),
the front-gate bet ratification, and skin/machine consistency under the
stage-vocabulary canon.

Stage vocabulary (CANON — `docs/architecture/stage-vocabulary.md`): the Scope's
`state` is the CONSERVED mechanical spec-lifecycle
(`draft → ready → in_progress → verified → ratified → done`); the optional
`phase` is the cognitive presentation skin
(`Frame → Shape → Build → Review → Ship`) and MUST equal the derivation from
`state` — this check refuses a stored skin that drifts from the machine (and the
enum keeps it from being a third vocabulary).

This is a **shared** check: it imports only the shared engine + scans files; it
MUST NOT import the v3 `coordination` module (that would be a `shared→v3` edge the
`version_boundary` check forbids). The canon constants below are therefore a
deliberate, drift-guarded duplicate of `coordination`'s — `test_ce_scope` asserts
they stay in sync.

This check is **defensive** — it governs CE's own work intake; it NEVER allocates
a container, spawns a run, or opens a socket. The pure coordination substrate is
`creator_engine_validator/coordination.py`; the live dispatch is a deferred seam.

See:
  - `docs/contracts/scope.md`
  - `docs/architecture/stage-vocabulary.md`
  - `schemas/scope.schema.yaml`
  - `creator_engine_validator/coordination.py`
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "ce_scope"
CONTRACT = "docs/contracts/scope.md"
SCHEMA = "schemas/scope.schema.yaml"
KIND_VALUE = "scope-record"

# Failure codes (explicit error classes).
CODE_SCHEMA = "VAL-SCOPE-SCHEMA"
CODE_INVALID = "VAL-SCOPE-INVALID"
CODE_DOR_INCOMPLETE = "VAL-SCOPE-DOR-INCOMPLETE"
CODE_APPETITE_INVALID = "VAL-SCOPE-APPETITE-INVALID"
CODE_RATIFICATION_UNBOUND = "VAL-SCOPE-RATIFICATION-UNBOUND"
CODE_STATE_INCONSISTENT = "VAL-SCOPE-STATE-INCONSISTENT"

# --- Canon constants (drift-guarded duplicate of `coordination`; see module doc) ---
READY_OR_LATER = frozenset({"ready", "in_progress", "verified", "ratified", "done"})
# The canon dual-mapping: mechanical spec-lifecycle state -> cognitive phase.
PHASE_BY_STATE = {
    "draft": "Frame",
    "ready": "Shape",
    "in_progress": "Build",
    "verified": "Review",
    "ratified": "Ship",
    "done": "Ship",
}
SPEND_UNITS = ("$", "%")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


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
    return state if state in PHASE_BY_STATE else ("draft" if state is None else str(state))


def _check_dor(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Ready-or-later Scopes MUST satisfy the DoR core (acceptance_criteria + appetite present)."""
    if _state_of(record) not in READY_OR_LATER:
        return []  # a draft Scope may still be framed/shaped (mirror definition_of_ready)
    errors: list[ValidationError] = []
    ac = record.get("acceptance_criteria")
    if not isinstance(ac, list) or not ac:
        errors.append(make_error(
            CODE_DOR_INCOMPLETE, path, "acceptance_criteria",
            "a ready-or-later Scope MUST have a non-empty acceptance_criteria list (the DoR core / test oracle)",
            CONTRACT,
        ))
    if record.get("appetite") is None:
        errors.append(make_error(
            CODE_DOR_INCOMPLETE, path, "appetite",
            "a ready-or-later Scope MUST declare an appetite (the fixed budget seeding the per-run spend cap)",
            CONTRACT,
        ))
    return errors


def _check_appetite(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """The appetite must be derivable to a run-scope spend_envelope (the G-5 join)."""
    appetite = record.get("appetite")
    if appetite is None:
        return []  # presence is a DoR concern; absence is handled there
    if not isinstance(appetite, dict):
        return [make_error(CODE_APPETITE_INVALID, path, "appetite", "appetite must be an object {amount, unit}", CONTRACT)]
    errors: list[ValidationError] = []
    amount = appetite.get("amount")
    if not isinstance(amount, (int, float)) or isinstance(amount, bool) or amount <= 0:
        errors.append(make_error(
            CODE_APPETITE_INVALID, path, "appetite/amount",
            "appetite.amount must be a number > 0 (a fixed budget, not an estimate)", CONTRACT,
        ))
    if appetite.get("unit") not in SPEND_UNITS:
        errors.append(make_error(
            CODE_APPETITE_INVALID, path, "appetite/unit",
            "appetite.unit must be '$' (API-USD fleet) or '%' (single-seat subscription meter)", CONTRACT,
        ))
    return errors


def _check_ratification(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Ready-or-later Scopes MUST carry the value-free front-gate bet ratification."""
    if _state_of(record) not in READY_OR_LATER:
        return []
    rat = record.get("ratification")
    ok = (
        isinstance(rat, dict)
        and isinstance(rat.get("approver_ref"), str) and bool(_HEX64_RE.match(rat["approver_ref"]))
        and isinstance(rat.get("ratified_scope_sha"), str) and bool(_HEX64_RE.match(rat["ratified_scope_sha"]))
    )
    if ok:
        return []
    return [make_error(
        CODE_RATIFICATION_UNBOUND, path, "ratification",
        "a ready-or-later Scope MUST carry a valid value-free bet ratification "
        "{approver_ref, ratified_scope_sha} (64-hex); the front gate gates dispatch",
        CONTRACT,
    )]


def _check_state_skin(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """A stored cognitive `phase` MUST equal the derivation from `state` (no skin/machine drift)."""
    phase = record.get("phase")
    if phase is None:
        return []
    expected = PHASE_BY_STATE.get(_state_of(record))
    if expected is not None and phase != expected:
        return [make_error(
            CODE_STATE_INCONSISTENT, path, "phase",
            f"stored cognitive phase {phase!r} != the canon derivation {expected!r} for state "
            f"{_state_of(record)!r}; the phase is a skin over the conserved machine, never a third vocabulary",
            CONTRACT,
        )]
    return []


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


def validate_scope(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one Scope record against the schema + coordination predicates."""
    errors: list[ValidationError] = []
    errors.extend(validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT))
    errors.extend(_check_dor(record, path))
    errors.extend(_check_appetite(record, path))
    errors.extend(_check_ratification(record, path))
    errors.extend(_check_state_skin(record, path))
    return errors


@register(
    CHECK_NAME,
    [CODE_SCHEMA, CODE_INVALID, CODE_DOR_INCOMPLETE, CODE_APPETITE_INVALID,
     CODE_RATIFICATION_UNBOUND, CODE_STATE_INCONSISTENT],
)
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_scope_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(record, dict):
            continue
        errors.extend(validate_scope(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
