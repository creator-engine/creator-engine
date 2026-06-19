"""Decision-Record validation (v3.5-C A-C1 — the durable decision artifact).

Validates **Decision Records** — Markdown files (`docs/decisions/ADR-NNNN-*.md`
ADRs in MADR 4.0.0 lineage; `docs/rfcs/RFC-NNNN-*.md` RFCs in Rust RFC + Final
Comment Period lineage) whose YAML front-matter carries
`kind: decision-record` — against `schemas/decision-record.schema.yaml` plus the
cross-field governance invariants:

- **accepted-is-human-ratified:** `status: accepted` REQUIRES the
  `ratification` block. Nothing in this check (or anywhere in CE) promotes a
  record to `accepted` — that transition is a human ratification event; this
  check only validates its recorded shape.
- **ratifier-is-concrete:** accepted records MUST name the concrete ratifier
  handle in `ratification.ratified_by`; role labels such as "the Operator" are
  placeholders and are rejected.
- **no privileged self-ratification:** for a privileged `mutation_class`
  (`PRIVILEGED_NAMES`), `ratification.ratified_by` MUST differ from every
  `decision_makers` entry (the ratifier is the *other* peer, never the owner).
- **supersede-with-link:** `status: superseded` REQUIRES a
  `crosswalk.superseded_by` id that resolves to a record discovered in the same
  scan (supersede-don't-delete; the link is the deletion-substitute).
- **FCP open-concern blocking (RFC form):** an `accepted` RFC with an `open`
  FCP concern is rejected — the Final Comment Period cannot complete while a
  blocking concern is open.

This is a **shared** check: it imports only the shared engine plus the shared
check module `mutation_class` (for `PRIVILEGED_NAMES` — a shared→shared edge);
it MUST NOT import a v3 module (the `version_boundary` CODE_UNALLOWED ratchet).

Shape + invariants ONLY: this check verifies a record's governance
well-formedness, never the *truth* of the decision it records.

See:
  - `docs/contracts/decision-record.md`
  - `docs/decisions/README.md` (ADR convention)
  - `docs/rfcs/README.md` (RFC + FCP convention)
  - `schemas/decision-record.schema.yaml`
"""

from __future__ import annotations

import datetime
import re
from pathlib import Path
from typing import Any, Iterable

from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register
from .mutation_class import PRIVILEGED_NAMES

CHECK_NAME = "decision_record"
CONTRACT = "docs/contracts/decision-record.md"
SCHEMA = "schemas/decision-record.schema.yaml"
KIND_VALUE = "decision-record"

# Failure codes (explicit error classes).
CODE_SCHEMA = "VAL-DR-SCHEMA"
CODE_INVALID = "VAL-DR-INVALID"
CODE_SELF_RATIFIED = "VAL-DR-SELF-RATIFIED"
CODE_SUPERSEDED_UNRESOLVED = "VAL-DR-SUPERSEDED-UNRESOLVED"
CODE_RATIFICATION_MISSING = "VAL-DR-RATIFICATION-MISSING"
CODE_FCP_OPEN_CONCERN = "VAL-DR-FCP-OPEN-CONCERN"
CODE_RATIFIER_PLACEHOLDER = "VAL-DR-RATIFIER-PLACEHOLDER"
# N=1 carve-out: local SHAPE guard for the honest `quorum: n1_solo` marker (the
# map-sensitive auto-expiry/laundered-quorum checks live in `peer_authority`,
# which owns the coordination-policy identity map). NEW failure class on the
# EXISTING check — no new check, no check-count delta.
CODE_N1_SOLO_MISUSED = "VAL-DR-N1-SOLO-MISUSED"

# The only lawful value of the honest solo-mode marker.
_N1_SOLO = "n1_solo"

# A file that *names itself* a decision record (ADR-/RFC-NNNN...) gets a parse
# error surfaced instead of being silently skipped.
_RECORD_FILENAME_RE = re.compile(r"^(ADR|RFC)-[0-9]{4}")
_TEMPLATE_SUFFIX = "-template.md"
_RATIFIER_HANDLE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_GENERIC_RATIFIER_LABELS = frozenset({
    "operator",
    "the operator",
    "source",
    "the source",
    "ratifier",
    "human",
    "placeholder",
    "unknown",
    "tbd",
    "todo",
    "n/a",
    "na",
    "none",
    "null",
})


def _is_template(path: Path) -> bool:
    return path.name.endswith(_TEMPLATE_SUFFIX)


def _split_front_matter(text: str) -> str | None:
    """Return the YAML front-matter segment of a Markdown document, or None."""
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for idx in range(1, len(lines)):
        if lines[idx].strip() in ("---", "..."):
            return "\n".join(lines[1:idx])
    return None


def _normalize_dates(value: Any) -> Any:
    """ISO-stringify YAML's native date/datetime scalars (bare dates are natural
    in hand-authored front-matter; the schema types them as ISO strings)."""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _normalize_dates(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_dates(v) for v in value]
    return value


def _load_front_matter(path: Path) -> tuple[Any, str | None]:
    """Parse a Markdown file's front-matter. Returns ``(data, parse_error)``."""
    try:
        import yaml
    except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("PyYAML is required; install validators/requirements.txt") from exc
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, str(exc)
    segment = _split_front_matter(text)
    if segment is None:
        return None, None
    try:
        data = yaml.safe_load(segment)
    except yaml.YAMLError as exc:
        return None, f"front-matter is not valid YAML: {exc}"
    return _normalize_dates(data), None


def iter_decision_records(
    paths: Iterable[Path],
) -> tuple[list[tuple[Path, dict[str, Any]]], list[ValidationError]]:
    """Discover Decision Records under ``paths``.

    Returns ``(records, errors)`` where ``records`` are
    ``(path, front_matter)`` pairs for files whose front-matter carries
    ``kind: decision-record``, and ``errors`` are parse failures for files
    that *name themselves* records (``ADR-NNNN``/``RFC-NNNN`` filenames) but
    cannot be read as one. Template files (``*-template.md``) are skipped.
    """
    seen: set[Path] = set()
    records: list[tuple[Path, dict[str, Any]]] = []
    errors: list[ValidationError] = []
    for raw in paths:
        path = Path(raw)
        if path.is_file() and path.suffix == ".md":
            candidates = [path]
        elif path.is_dir():
            candidates = sorted(path.rglob("*.md"))
        else:
            candidates = []
        for candidate in candidates:
            if _is_template(candidate):
                continue
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            data, parse_error = _load_front_matter(candidate)
            if parse_error is not None:
                if _RECORD_FILENAME_RE.match(candidate.name):
                    errors.append(make_error(CODE_INVALID, candidate, "", parse_error, CONTRACT))
                continue
            if isinstance(data, dict) and data.get("kind") == KIND_VALUE:
                records.append((candidate, data))
    return records, errors


def _check_ratification_presence(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """`accepted` is a human-ratification event — its attestation must be recorded."""
    if record.get("status") != "accepted":
        return []
    if isinstance(record.get("ratification"), dict):
        return []
    return [make_error(
        CODE_RATIFICATION_MISSING, path, "ratification",
        "an accepted Decision Record MUST carry the ratification block "
        "{ratified_by, ratified_at, ratification_prompt_sha}; `accepted` is a "
        "human-ratification event, never an agent promotion",
        CONTRACT,
    )]


def _check_concrete_ratifier(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Accepted records name the actual ratifier handle, not a generic role."""
    if record.get("status") != "accepted":
        return []
    ratification = record.get("ratification")
    if not isinstance(ratification, dict):
        return []
    ratified_by = ratification.get("ratified_by")
    if not isinstance(ratified_by, str):
        return []
    normalized = " ".join(ratified_by.strip().lower().split())
    if (
        normalized in _GENERIC_RATIFIER_LABELS
        or not _RATIFIER_HANDLE_RE.match(ratified_by.strip())
    ):
        return [make_error(
            CODE_RATIFIER_PLACEHOLDER, path, "ratification/ratified_by",
            "accepted Decision Records MUST record the concrete ratifier handle "
            "in ratification.ratified_by; generic role labels/placeholders such "
            f"as {ratified_by!r} are not stable enough for multi-operator audit",
            CONTRACT,
        )]
    return []


def _check_self_ratification(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Privileged classes: the ratifier must be independent of the decision makers."""
    if record.get("mutation_class") not in PRIVILEGED_NAMES:
        return []
    ratification = record.get("ratification")
    if not isinstance(ratification, dict):
        return []
    ratified_by = ratification.get("ratified_by")
    makers = record.get("decision_makers")
    makers_list = makers if isinstance(makers, list) else []
    if isinstance(ratified_by, str) and ratified_by in makers_list:
        return [make_error(
            CODE_SELF_RATIFIED, path, "ratification/ratified_by",
            f"privileged mutation_class {record.get('mutation_class')!r} requires an "
            f"independent ratifier: ratified_by {ratified_by!r} is one of the "
            "decision_makers (no self-ratification)",
            CONTRACT,
        )]
    return []


def _check_superseded_link(
    record: dict[str, Any], path: Path, known_ids: frozenset[str]
) -> list[ValidationError]:
    """`superseded` requires a resolvable successor link (supersede-don't-delete)."""
    if record.get("status") != "superseded":
        return []
    crosswalk = record.get("crosswalk")
    target = crosswalk.get("superseded_by") if isinstance(crosswalk, dict) else None
    if not isinstance(target, str) or not target:
        return [make_error(
            CODE_SUPERSEDED_UNRESOLVED, path, "crosswalk/superseded_by",
            "a superseded Decision Record MUST link its successor via "
            "crosswalk.superseded_by (supersede-don't-delete)",
            CONTRACT,
        )]
    if target not in known_ids:
        return [make_error(
            CODE_SUPERSEDED_UNRESOLVED, path, "crosswalk/superseded_by",
            f"crosswalk.superseded_by {target!r} does not resolve to a Decision "
            "Record discovered in this scan (the successor must exist)",
            CONTRACT,
        )]
    return []


def _check_fcp_concerns(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """RFC form: the FCP cannot complete while a blocking concern is open."""
    if record.get("record_type") != "rfc" or record.get("status") != "accepted":
        return []
    fcp = record.get("fcp")
    concerns = fcp.get("concerns") if isinstance(fcp, dict) else None
    if not isinstance(concerns, list):
        return []
    open_names = [
        c.get("name") for c in concerns
        if isinstance(c, dict) and c.get("status") == "open"
    ]
    if open_names:
        return [make_error(
            CODE_FCP_OPEN_CONCERN, path, "fcp/concerns",
            f"an accepted RFC cannot carry open FCP concerns ({open_names!r}); "
            "the Final Comment Period cannot complete while a blocking concern is open",
            CONTRACT,
        )]
    return []


def _check_n1_solo_quorum(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Local shape guard for `ratification.quorum: n1_solo`.

    The honest solo-mode marker is meaningful ONLY on an `accepted` privileged
    Decision Record. This check owns that shape rule and the assurance that the
    marker never relaxes privileged self-ratification (the existing
    VAL-DR-SELF-RATIFIED check is unconditional and still applies). It does NOT
    claim auto-expiry — that is map-sensitive and owned by `peer_authority`,
    which holds the current coordination-policy identity map.
    """
    ratification = record.get("ratification")
    quorum = ratification.get("quorum") if isinstance(ratification, dict) else None
    if quorum is None:
        return []  # absent ⇒ ordinary team-mode record (schema pins any value to n1_solo)
    problems: list[str] = []
    if record.get("status") != "accepted":
        problems.append(
            f"it is set on a non-accepted record (status={record.get('status')!r}); the marker "
            "records a completed ratification, so it is meaningful only on `accepted` records"
        )
    if record.get("mutation_class") not in PRIVILEGED_NAMES:
        problems.append(
            f"it is set on a non-privileged record (mutation_class={record.get('mutation_class')!r}); "
            "the solo quorum mode is reserved for privileged ratifications"
        )
    if not problems:
        return []
    return [make_error(
        CODE_N1_SOLO_MISUSED, path, "ratification/quorum",
        "quorum: n1_solo is meaningful only on an accepted privileged Decision Record: "
        + "; ".join(problems)
        + ". (The map-sensitive auto-expiry / laundered-quorum checks are owned by "
        "peer_authority, which holds the identity map.)",
        CONTRACT,
    )]


def validate_decision_record(
    record: dict[str, Any], path: Path, known_ids: frozenset[str] = frozenset()
) -> list[ValidationError]:
    """Validate one Decision Record front-matter against schema + invariants."""
    errors: list[ValidationError] = []
    errors.extend(validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT))
    errors.extend(_check_ratification_presence(record, path))
    errors.extend(_check_concrete_ratifier(record, path))
    errors.extend(_check_self_ratification(record, path))
    errors.extend(_check_superseded_link(record, path, known_ids))
    errors.extend(_check_fcp_concerns(record, path))
    errors.extend(_check_n1_solo_quorum(record, path))
    return errors


@register(
    CHECK_NAME,
    [CODE_SCHEMA, CODE_INVALID, CODE_SELF_RATIFIED, CODE_SUPERSEDED_UNRESOLVED,
     CODE_RATIFICATION_MISSING, CODE_FCP_OPEN_CONCERN,
     CODE_RATIFIER_PLACEHOLDER, CODE_N1_SOLO_MISUSED],
)
def run(paths: Iterable[Path]) -> CheckResult:
    records, errors = iter_decision_records([Path(p) for p in paths])
    known_ids = frozenset(
        rec.get("id") for _, rec in records if isinstance(rec.get("id"), str)
    )
    for record_path, record in records:
        errors.extend(validate_decision_record(record, record_path, known_ids))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
