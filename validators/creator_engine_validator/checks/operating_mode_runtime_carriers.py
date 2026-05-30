"""G2.002.1 operating-mode runtime-carrier validator.

G2.002.0 (`operating_mode_policy`) defined the operating-mode policy substrate
(mode/autonomy enums, policy schema, floor rules) as shape-only. G2.002.1
propagates that substrate into runtime carriers and this check enforces floor
preservation on those carriers:

* Active-Work Ledger records (``kind == active-work-ledger-record``) that carry
  any operating-mode carrier field (``operating_mode``, ``autonomy_class``,
  ``lane_kind``, ``ratification_evidence_ref``); and
* operating-mode-policy sidecars that carry a ``runtime_carriers`` block (a list
  of carrier descriptors), either top-level or under ``operating_mode_policy``.

Carriers are PURE: they record posture and mint no authority. The Assignment
Envelope and Operator ratification remain the substantive authority. This check
reuses the G2.002.0 substrate helpers rather than re-deriving authority
semantics, and never relaxes the Operator-only privileged floor.

Records/sidecars that carry no carrier fields are ignored, so pre-v4 ledger
records and substrate-only policy sidecars are untouched.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from . import register
from .operating_mode_policy import (
    AUTONOMY_CLASSES,
    OPERATING_MODES,
    _has_meaningful_policy_pointer,
    _normalize_token,
    _subtree_has_active_agent_ratifier,
)

CHECK_NAME = "operating_mode_runtime_carriers"
CONTRACT = "specs/v2/002-operating-mode-substrate/spec.ce.yml#operating_mode_policy"

CODE_MODE_ENUM = "VAL-CARRIER-MODE-ENUM"
CODE_AUTONOMY_ENUM = "VAL-CARRIER-AUTONOMY-ENUM"
CODE_LANE_KIND_ENUM = "VAL-CARRIER-LANE-KIND-ENUM"
CODE_ELEVATION_REQUIRES_RATIFICATION = "VAL-CARRIER-ELEVATION-REQUIRES-RATIFICATION"
CODE_RESERVED_AUTONOMY_ACTIVE = "VAL-CARRIER-RESERVED-AUTONOMY-ACTIVE"
CODE_AGENT_RATIFIER_ACTIVE = "VAL-CARRIER-AGENT-RATIFIER-ACTIVE"
CODE_MIGRATED_DEFAULT = "VAL-CARRIER-MIGRATED-DEFAULT-STRICT"
CODE_ROLE_SEPARATION = "VAL-CARRIER-ROLE-SEPARATION"
CODE_SCHEMA = "VAL-CARRIER-SCHEMA"

LANE_KINDS = frozenset({"read-only", "implementation", "review", "approval", "merge", "audit"})
# Lane kinds that carry out a privileged mutation and therefore require an
# inherited Operator ratification-evidence pointer.
PRIVILEGED_LANE_KINDS = frozenset({"approval", "merge"})
ELEVATED_MODES = frozenset({"auto", "transcendence"})
CARRIER_FIELDS = ("operating_mode", "autonomy_class", "lane_kind", "ratification_evidence_ref")
LEDGER_KIND = "active-work-ledger-record"
_SCANNED_YAML_SUFFIXES = {".yml", ".yaml"}


def _pointer(parts: tuple[Any, ...]) -> str:
    rendered = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(rendered) if rendered else "/"


def _err(code: str, path: Path, parts: tuple[Any, ...], message: str) -> ValidationError:
    return make_error(code, path, _pointer(parts), message, CONTRACT)


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _is_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts or "templates" in parts


def validate_carrier(
    carrier: Any, path: Path, parts: tuple[Any, ...]
) -> list[ValidationError]:
    """Validate one runtime-carrier descriptor against the G2.002.1 floor.

    ``carrier`` may be an Active-Work Ledger record or a ``runtime_carriers``
    entry; only the carrier fields are read. Absent fields resolve to ``strict``
    / conservative and are not errors.
    """
    errors: list[ValidationError] = []
    if not isinstance(carrier, dict):
        return [_err(CODE_SCHEMA, path, parts, "runtime carrier must be a mapping")]

    raw_mode = carrier.get("operating_mode")
    mode = _normalize_token(raw_mode) if raw_mode is not None else "strict"
    if raw_mode is not None and mode not in OPERATING_MODES:
        errors.append(
            _err(
                CODE_MODE_ENUM,
                path,
                parts + ("operating_mode",),
                "operating_mode carrier must be one of strict, auto, transcendence",
            )
        )

    raw_autonomy = carrier.get("autonomy_class")
    autonomy = _normalize_token(raw_autonomy) if raw_autonomy is not None else ""
    if raw_autonomy is not None and autonomy not in AUTONOMY_CLASSES:
        errors.append(
            _err(
                CODE_AUTONOMY_ENUM,
                path,
                parts + ("autonomy_class",),
                "autonomy_class carrier is not a recognized G2.002.0 value",
            )
        )
    if autonomy == "reserved_future_agent_ratification":
        errors.append(
            _err(
                CODE_RESERVED_AUTONOMY_ACTIVE,
                path,
                parts + ("autonomy_class",),
                "reserved_future_agent_ratification is a schema-visible placeholder and MUST NOT be an active carrier autonomy",
            )
        )

    raw_lane_kind = carrier.get("lane_kind")
    lane_kind = _normalize_lane_kind(raw_lane_kind) if raw_lane_kind is not None else ""
    if raw_lane_kind is not None and lane_kind not in LANE_KINDS:
        errors.append(
            _err(
                CODE_LANE_KIND_ENUM,
                path,
                parts + ("lane_kind",),
                "lane_kind carrier must be one of read-only, implementation, review, approval, merge, audit",
            )
        )

    ratification_present = _has_meaningful_policy_pointer(carrier.get("ratification_evidence_ref"))

    if mode in ELEVATED_MODES and not ratification_present:
        errors.append(
            _err(
                CODE_ELEVATION_REQUIRES_RATIFICATION,
                path,
                parts + ("ratification_evidence_ref",),
                f"operating_mode {mode!r} carrier requires an Operator-ratified ratification_evidence_ref",
            )
        )
    if lane_kind in PRIVILEGED_LANE_KINDS and not ratification_present:
        errors.append(
            _err(
                CODE_ELEVATION_REQUIRES_RATIFICATION,
                path,
                parts + ("ratification_evidence_ref",),
                f"privileged lane_kind {lane_kind!r} carrier requires an inherited ratification_evidence_ref",
            )
        )

    if _subtree_has_active_agent_ratifier(carrier):
        errors.append(
            _err(
                CODE_AGENT_RATIFIER_ACTIVE,
                path,
                parts,
                "agent_ratifier MUST remain reserved-inactive; a carrier MUST NOT bind it to active authority",
            )
        )

    migrated_default = carrier.get("default_for_migrated_v1_tenants", carrier.get("migrated_default"))
    if migrated_default is not None and _normalize_token(migrated_default) != "strict":
        errors.append(
            _err(
                CODE_MIGRATED_DEFAULT,
                path,
                parts + ("default_for_migrated_v1_tenants",),
                "migrated/absent carrier operating mode must resolve to strict; elevation is never inferred",
            )
        )

    # Author/approver role separation: a privileged lane kind (approval/merge)
    # carries an Operator-ratified privileged mutation; it MUST NOT be delegated
    # to a non-privileged autonomy class.
    if lane_kind in PRIVILEGED_LANE_KINDS and autonomy == "delegated_non_privileged":
        errors.append(
            _err(
                CODE_ROLE_SEPARATION,
                path,
                parts + ("autonomy_class",),
                f"privileged lane_kind {lane_kind!r} MUST NOT be delegated to autonomy_class delegated_non_privileged",
            )
        )

    return errors


def _normalize_lane_kind(value: Any) -> str:
    # lane_kind enum values use hyphens (`read-only`); compare case-insensitively
    # without collapsing the hyphen, so an underscore variant is not silently
    # accepted as a different enum member.
    return str(value).strip().lower()


def _carrier_descriptors(data: dict[str, Any]) -> list[Any] | None:
    """Return the ``runtime_carriers`` list for a policy sidecar, else ``None``."""
    if isinstance(data.get("runtime_carriers"), list):
        return data["runtime_carriers"]
    policy = data.get("operating_mode_policy")
    if isinstance(policy, dict) and isinstance(policy.get("runtime_carriers"), list):
        return policy["runtime_carriers"]
    return None


def _record_has_carrier_fields(record: dict[str, Any]) -> bool:
    return any(field in record for field in CARRIER_FIELDS)


def validate_file(path: Path) -> list[ValidationError]:
    if path.suffix.lower() not in _SCANNED_YAML_SUFFIXES:
        return []
    try:
        data = load_yaml(path)
    except LoaderError:
        return []
    if not isinstance(data, dict):
        return []

    if data.get("kind") == LEDGER_KIND and _record_has_carrier_fields(data):
        return validate_carrier(data, path, ())

    descriptors = _carrier_descriptors(data)
    if descriptors is not None:
        errors: list[ValidationError] = []
        for index, carrier in enumerate(descriptors):
            errors.extend(validate_carrier(carrier, path, ("runtime_carriers", index)))
        return errors

    return []


def iter_scanned_files(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            candidates = [path]
        elif path.is_dir():
            candidates = sorted(p for p in path.rglob("*") if p.is_file())
        else:
            candidates = []
        for candidate in candidates:
            if candidate.suffix.lower() not in _SCANNED_YAML_SUFFIXES:
                continue
            if _is_tmp_artifact(candidate) or _is_excluded(candidate):
                continue
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            out.append(candidate)
    return out


@register(
    CHECK_NAME,
    [
        CODE_MODE_ENUM,
        CODE_AUTONOMY_ENUM,
        CODE_LANE_KIND_ENUM,
        CODE_ELEVATION_REQUIRES_RATIFICATION,
        CODE_RESERVED_AUTONOMY_ACTIVE,
        CODE_AGENT_RATIFIER_ACTIVE,
        CODE_MIGRATED_DEFAULT,
        CODE_ROLE_SEPARATION,
        CODE_SCHEMA,
    ],
)
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for file_path in iter_scanned_files(paths):
        errors.extend(validate_file(file_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
