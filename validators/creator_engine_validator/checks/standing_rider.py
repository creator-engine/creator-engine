"""Read-only validation for the CE605 standing-rider evidence stream."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register
from .decision_record import iter_decision_records, validate_decision_record

CHECK_NAME = "standing_rider"
CONTRACT = "docs/decisions/ADR-0605-standing-rider-cadence.md"
SCHEMA = "schemas/standing-rider-note.schema.yaml"
ADR_RELATIVE_PATH = Path("docs/decisions/ADR-0605-standing-rider-cadence.md")
NOTES_RELATIVE_PATH = Path("docs/decisions/ce605-standing-rider-notes.ndjson")
CADENCE = timedelta(days=7)
GENESIS_PREDECESSOR = "0" * 64

CODE_SCHEMA = "VAL-SR-SCHEMA"
CODE_ARTIFACT = "VAL-SR-ARTIFACT"
CODE_CANONICAL = "VAL-SR-CANONICAL"
CODE_DIGEST = "VAL-SR-DIGEST"
CODE_CHAIN = "VAL-SR-CHAIN"
CODE_CLOCK = "VAL-SR-CLOCK"
CODE_CADENCE = "VAL-SR-CADENCE"
CODE_SOURCE_REF = "VAL-SR-SOURCE-REF"
CODE_TRIPWIRE = "VAL-SR-TRIPWIRE"
CODE_UNRATIFIED = "VAL-SR-UNRATIFIED"

_PRIVATE_REFERENCE = re.compile(
    r"(?:https?://|\\b(?:private|secret|token|credential|password|key)\\b|^/|\\.ce/state)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CadenceEvaluation:
    due: bool
    next_due_at: datetime
    missed_boundaries: int


def canonical_note_bytes(note: dict[str, Any], *, include_digest: bool = True) -> bytes:
    """Return the sole on-disk representation for a rider note."""
    value = dict(note)
    if not include_digest:
        value.pop("note_sha256", None)
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def with_note_sha256(note: dict[str, Any]) -> dict[str, Any]:
    """Return a copy carrying the digest of its digest-free canonical bytes."""
    value = dict(note)
    value.pop("note_sha256", None)
    value["note_sha256"] = hashlib.sha256(canonical_note_bytes(value, include_digest=False)).hexdigest()
    return value


def _as_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def evaluate_cadence(last_note: dict[str, Any], now: datetime) -> CadenceEvaluation:
    """Evaluate one deterministic cadence step without reading wall time."""
    due_at = _as_datetime(last_note.get("cadence_due_at"))
    if due_at is None:
        raise ValueError("cadence_due_at must be an ISO-8601 UTC timestamp")
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    observed = now.astimezone(UTC)
    if observed < due_at:
        return CadenceEvaluation(False, due_at, 0)
    missed = int((observed - due_at) // CADENCE)
    return CadenceEvaluation(True, due_at + CADENCE, missed)


def _error(code: str, path: Path, field: str, message: str) -> ValidationError:
    return make_error(code, path, field, message, CONTRACT)


def _expected_tripwire(note: dict[str, Any]) -> str:
    source_state = note.get("source_state")
    assessment = note.get("assessment")
    if source_state == "unavailable":
        return "source_unavailable"
    if source_state in {"stale", "contradictory"} or assessment in {"change_detected", "deferred"}:
        return "immediate_review_required"
    return "clear"


def validate_note(
    note: dict[str, Any],
    path: Path,
    *,
    previous: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> list[ValidationError]:
    """Validate one note and, when supplied, its predecessor and clock seam."""
    errors = validate_with_schema(note, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT)
    expected_digest = hashlib.sha256(canonical_note_bytes(note, include_digest=False)).hexdigest()
    if note.get("note_sha256") != expected_digest:
        errors.append(_error(CODE_DIGEST, path, "note_sha256", "does not match digest-free canonical note bytes"))

    refs = note.get("source_refs")
    if isinstance(refs, list):
        for index, ref in enumerate(refs):
            value = ref.get("path_or_digest") if isinstance(ref, dict) else None
            if isinstance(value, str) and _PRIVATE_REFERENCE.search(value):
                errors.append(_error(
                    CODE_SOURCE_REF,
                    path,
                    f"source_refs/{index}/path_or_digest",
                    "must be a public-safe path or opaque digest, not a URL or private-looking reference",
                ))

    expected_tripwire = _expected_tripwire(note)
    if note.get("tripwire") != expected_tripwire:
        errors.append(_error(
            CODE_TRIPWIRE,
            path,
            "tripwire",
            f"must be {expected_tripwire!r} for source_state={note.get('source_state')!r} "
            f"and assessment={note.get('assessment')!r}",
        ))
    if note.get("assessment") == "no_change" and note.get("source_state") != "authenticated":
        errors.append(_error(CODE_TRIPWIRE, path, "assessment", "no_change requires authenticated sources"))

    observed_at = _as_datetime(note.get("observed_at"))
    if now is not None:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        clock = now.astimezone(UTC)
        if observed_at is not None and observed_at > clock:
            errors.append(_error(CODE_CLOCK, path, "observed_at", "cannot be later than injected now"))
        try:
            cadence = evaluate_cadence(note, clock)
        except ValueError:
            cadence = None
        if cadence is not None and cadence.due:
            errors.append(_error(
                CODE_CADENCE,
                path,
                "cadence_due_at",
                "a note is due; append exactly one deterministic next-boundary note or require immediate review",
            ))

    if previous is None:
        if note.get("sequence") == 1 and note.get("previous_note_sha256") != GENESIS_PREDECESSOR:
            errors.append(_error(CODE_CHAIN, path, "previous_note_sha256", "genesis note must use the all-zero predecessor"))
    else:
        expected_sequence = previous.get("sequence") + 1 if isinstance(previous.get("sequence"), int) else None
        if note.get("sequence") != expected_sequence:
            errors.append(_error(CODE_CHAIN, path, "sequence", "must advance exactly one from its predecessor"))
        if note.get("previous_note_sha256") != previous.get("note_sha256"):
            errors.append(_error(CODE_CHAIN, path, "previous_note_sha256", "does not bind the accepted predecessor digest"))
        previous_due = _as_datetime(previous.get("cadence_due_at"))
        current_due = _as_datetime(note.get("cadence_due_at"))
        if previous_due is not None and current_due != previous_due + CADENCE:
            errors.append(_error(
                CODE_CADENCE,
                path,
                "cadence_due_at",
                "must be exactly one cadence boundary after the predecessor",
            ))
        previous_observed = _as_datetime(previous.get("observed_at"))
        if previous_observed is not None and observed_at is not None and observed_at < previous_observed:
            errors.append(_error(CODE_CHAIN, path, "observed_at", "cannot predate its predecessor"))
    return errors


def validate_note_stream(path: Path, *, now: datetime | None = None) -> list[ValidationError]:
    """Validate a canonical NDJSON stream without writing or fetching anything."""
    errors: list[ValidationError] = []
    try:
        payload = path.read_bytes()
    except OSError as exc:
        return [_error(CODE_ARTIFACT, path, "", str(exc))]
    if not payload.endswith(b"\n"):
        errors.append(_error(CODE_CANONICAL, path, "", "NDJSON stream must end with one newline"))
    previous: dict[str, Any] | None = None
    for line_number, raw_line in enumerate(payload.splitlines(keepends=True), start=1):
        if not raw_line.endswith(b"\n"):
            continue
        try:
            note = json.loads(raw_line)
        except json.JSONDecodeError:
            errors.append(_error(CODE_CANONICAL, path, str(line_number), "each line must be one canonical JSON object"))
            continue
        if not isinstance(note, dict):
            errors.append(_error(CODE_SCHEMA, path, str(line_number), "each NDJSON line must decode to an object"))
            continue
        if raw_line != canonical_note_bytes(note):
            errors.append(_error(CODE_CANONICAL, path, str(line_number), "line is not sorted-key canonical JSON plus newline"))
        errors.extend(validate_note(note, path, previous=previous, now=now))
        previous = note
    if previous is None:
        errors.append(_error(CODE_ARTIFACT, path, "", "canonical stream must contain at least one note"))
    return errors


def _repo_roots(paths: Iterable[Path]) -> list[Path]:
    roots: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        candidate = Path(raw)
        start = candidate if candidate.is_dir() else candidate.parent
        for parent in (start, *start.parents):
            if (parent / "docs").is_dir():
                resolved = parent.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    roots.append(parent)
                break
    return roots


def _note_candidates(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for path in root.rglob("*.ndjson"):
        if path.name == NOTES_RELATIVE_PATH.name:
            candidates.append(path)
            continue
        try:
            if '"rider_id":"CE605"' in path.read_text(encoding="utf-8"):
                candidates.append(path)
        except OSError:
            continue
    return sorted(candidates)


def validate_repo(root: Path) -> list[ValidationError]:
    """Validate CE605's fixed artifacts under one repository root."""
    errors: list[ValidationError] = []
    adr = root / ADR_RELATIVE_PATH
    notes = root / NOTES_RELATIVE_PATH
    if not adr.is_file():
        errors.append(_error(CODE_ARTIFACT, adr, "", "missing canonical ADR-0605 artifact"))
    else:
        records, discovery_errors = iter_decision_records([adr])
        errors.extend(discovery_errors)
        if len(records) != 1:
            errors.append(_error(CODE_ARTIFACT, adr, "", "ADR-0605 must be one decision-record artifact"))
        else:
            _, record = records[0]
            errors.extend(validate_decision_record(record, adr, frozenset({"ADR-0605"})))
            if record.get("status") != "accepted":
                errors.append(_error(
                    CODE_UNRATIFIED,
                    adr,
                    "status",
                    "standing rider is not active until ADR-0605 is human-ratified; immediate review is required",
                ))
    candidates = _note_candidates(root)
    if candidates != [notes]:
        errors.append(_error(
            CODE_ARTIFACT,
            notes,
            "",
            "expected exactly one canonical CE605 note stream and no alternate or duplicate artifact",
        ))
    if notes.is_file():
        errors.extend(validate_note_stream(notes))
    return errors


@register(
    CHECK_NAME,
    [CODE_SCHEMA, CODE_ARTIFACT, CODE_CANONICAL, CODE_DIGEST, CODE_CHAIN, CODE_CLOCK,
     CODE_CADENCE, CODE_SOURCE_REF, CODE_TRIPWIRE, CODE_UNRATIFIED],
)
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for root in _repo_roots(paths):
        errors.extend(validate_repo(root))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
