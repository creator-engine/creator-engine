"""Storage-tier advisory-finding validation (v3.5-C A-C2 — design §A.3/§A.2).

Validates **storage-tier findings** (`kind: storage-tier-finding`) against
`schemas/storage-tier-finding.schema.yaml` plus the governance invariants:

- **No auto-promotion (the hard invariant):** a finding is ADVISORY; the
  `promotion.promoted: true` transition is valid ONLY with a
  `promotion.ratification_ref` pointing at the human-ratification record on
  the evidence-spine. There exists **no code path in this module (or anywhere
  in CE) that flips `promoted` without a ratification reference** — the only
  constructor (:func:`emit_finding`) always emits `advisory: true`,
  `promoted: false`, and this module deliberately defines no
  ``promote()``.
- **Noise stays local:** a part classified `instance-local-noise` cannot be
  proposed into a shared tier (`repo-docs` / `ops-private`).
- **Split form:** a finding may split one artifact across tiers — one
  classification entry per part, with **distinct** `part_ref`s.

The 5-stage triage loop (read-only classify → schema finding → deterministic
gates → discard-on-drift → guarded mutation) is RE-IMPLEMENTED here as pure
helpers (:data:`TRIAGE_STAGES`, :func:`emit_finding`) — this is a **shared**
check and MUST NOT import a v3 module (the `version_boundary` CODE_UNALLOWED
ratchet). The *live* LLM classification call is a deferred seam: this gate
ships the advisory finding contract + policy only; nothing here opens an
issue, writes to a remote, or promotes.

The rule governing tier choice is itself a ratified governance Decision
Record — `docs/decisions/ADR-0001-public-private-storage-policy.md`,
validated by the A-C1 `decision_record` check: the classification rule is the
same kind of object as the things it classifies.

See:
  - `docs/contracts/storage-tier-finding.md`
  - `docs/decisions/ADR-0001-public-private-storage-policy.md`
  - `schemas/storage-tier-finding.schema.yaml`
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "storage_tier_finding"
CONTRACT = "docs/contracts/storage-tier-finding.md"
SCHEMA = "schemas/storage-tier-finding.schema.yaml"
KIND_VALUE = "storage-tier-finding"

# Failure codes (explicit error classes).
CODE_SCHEMA = "VAL-STF-SCHEMA"
CODE_INVALID = "VAL-STF-INVALID"
CODE_AUTO_PROMOTED = "VAL-STF-AUTO-PROMOTED"
CODE_SPLIT_DUPLICATE_PART = "VAL-STF-SPLIT-DUPLICATE-PART"
CODE_NOISE_SHARED_TIER = "VAL-STF-NOISE-SHARED-TIER"

TIERS = frozenset({"instance-local", "repo-docs", "ops-private"})
SHARED_TIERS = frozenset({"repo-docs", "ops-private"})
RELEVANCE = frozenset({"project-relevant", "team-relevant", "instance-local-noise"})

#: The 5-stage triage loop the advisory classifier reuses (design §A.3) —
#: re-implemented as data here (shared check; no v3 import). The finding this
#: check validates is the *output of stage 2*; stages 3–5 are deterministic
#: gates outside the LLM, and stage 5 (guarded mutation) happens ONLY after a
#: human ratifies (the `promotion.ratification_ref`).
TRIAGE_STAGES: tuple[str, ...] = (
    "read_only_classify",
    "schema_finding",
    "deterministic_gates",
    "discard_on_drift",
    "guarded_mutation",
)


def emit_finding(
    artifact_ref: str, classifications: list[dict[str, Any]]
) -> dict[str, Any]:
    """The ONLY finding constructor: born advisory, born unpromoted.

    Pure stage-2 helper (`schema_finding`): wraps proposed classifications
    into a record that ALWAYS carries ``advisory: true`` and
    ``promotion: {promoted: false}``. There is deliberately no parameter, and
    no sibling function, that emits a promoted finding — promotion is a
    human-ratification event recorded on the spine, never an emit-time state.
    """
    return {
        "kind": KIND_VALUE,
        "schema_version": "1",
        "artifact_ref": artifact_ref,
        "advisory": True,
        "classifications": list(classifications),
        "promotion": {"promoted": False},
    }


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts or "templates" in parts


def iter_finding_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate storage-tier-finding files under ``paths``."""
    seen: set[Path] = set()
    records: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if _looks_like_yaml(path) and not _is_under_excluded(path):
            candidates = [path]
        elif path.is_dir():
            candidates = [
                p for p in sorted(path.rglob("*.yml")) + sorted(path.rglob("*.yaml"))
                if _looks_like_yaml(p) and not _is_under_excluded(p)
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
            if isinstance(data, dict) and data.get("kind") == KIND_VALUE:
                seen.add(resolved)
                records.append(candidate)
    return records


def _check_no_auto_promotion(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """`promoted: true` is valid ONLY with a spine ratification reference."""
    promotion = record.get("promotion")
    if not isinstance(promotion, dict) or promotion.get("promoted") is not True:
        return []
    ref = promotion.get("ratification_ref")
    if isinstance(ref, str) and ref:
        return []
    return [make_error(
        CODE_AUTO_PROMOTED, path, "promotion/ratification_ref",
        "a finding with promoted: true MUST reference the human-ratification "
        "record on the evidence-spine (ratification_ref); findings are advisory "
        "— nothing self-promotes",
        CONTRACT,
    )]


def _check_split_parts(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Split form: every classified part must be distinct."""
    classifications = record.get("classifications")
    if not isinstance(classifications, list):
        return []
    errors: list[ValidationError] = []
    seen: dict[str, int] = {}
    for idx, entry in enumerate(classifications):
        if not isinstance(entry, dict):
            continue
        part = entry.get("part_ref")
        if not isinstance(part, str):
            continue
        if part in seen:
            errors.append(make_error(
                CODE_SPLIT_DUPLICATE_PART, path, f"classifications/{idx}/part_ref",
                f"duplicate part_ref {part!r} (first at /classifications/{seen[part]}); "
                "a split classifies each part exactly once",
                CONTRACT,
            ))
        else:
            seen[part] = idx
    return errors


def _check_noise_stays_local(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Instance-local noise is never proposed into a shared tier."""
    classifications = record.get("classifications")
    if not isinstance(classifications, list):
        return []
    errors: list[ValidationError] = []
    for idx, entry in enumerate(classifications):
        if not isinstance(entry, dict):
            continue
        if entry.get("relevance") == "instance-local-noise" and entry.get("tier") in SHARED_TIERS:
            errors.append(make_error(
                CODE_NOISE_SHARED_TIER, path, f"classifications/{idx}/tier",
                f"part {entry.get('part_ref')!r} classified instance-local-noise "
                f"cannot be proposed into shared tier {entry.get('tier')!r}; "
                "noise stays instance-local",
                CONTRACT,
            ))
    return errors


def validate_finding(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one storage-tier finding against the schema + invariants."""
    errors: list[ValidationError] = []
    errors.extend(validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT))
    errors.extend(_check_no_auto_promotion(record, path))
    errors.extend(_check_split_parts(record, path))
    errors.extend(_check_noise_stays_local(record, path))
    return errors


@register(
    CHECK_NAME,
    [CODE_SCHEMA, CODE_INVALID, CODE_AUTO_PROMOTED, CODE_SPLIT_DUPLICATE_PART,
     CODE_NOISE_SHARED_TIER],
)
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_finding_records([Path(p) for p in paths]):
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(record, dict):
            continue
        errors.extend(validate_finding(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
