"""Completion Report → envelope pairing check (PCO Slice 0.5).

Implements CR-002 from
``docs/operations/COMPLETION_REPORT_PROTOCOL.md`` §l.

For every Completion Report sidecar discovered under the scanned
paths, this check verifies envelope pairing:

* If the report's ``envelope_ref`` resolves to a real file on disk
  (relative to the repo root and to the current working directory),
  the file's SHA256 MUST equal the report's ``envelope_sha256``.
* If the envelope file is not present on disk (the typical case
  for ``.hermes/``-prefixed envelopes that live under the
  local-runtime ignore), the check is satisfied for that report
  (the envelope is presumed to live under untracked runtime state).
* If multiple reports point at the same envelope and at least two
  declare ``outcome: completed``, the duplicate-completed condition
  fails. Multiple reports with mixed outcomes (e.g., one ``partial``
  followed by a final ``completed``) are accepted; the substrate
  records gate retries.

Slice 0.5 scope discipline:

* The check MUST NOT implement the Hermes final-answer hook
  (Slice 0.5R).
* The check MUST NOT require an Active-Work Ledger to be present;
  the report→envelope pairing is independent of the ledger.

Failures cite ``CR-002`` and the prose contract at
``docs/operations/COMPLETION_REPORT_PROTOCOL.md``.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from . import register
from .completion_report_schema import iter_completion_report_records

CHECK_NAME = "completion_report_required_for_envelope"
CONTRACT = "docs/operations/COMPLETION_REPORT_PROTOCOL.md"
CODE_PAIRING = "CR-002"


def _repo_root_for(path: Path) -> Path:
    """Best-effort locate the repo root for resolving envelope_ref."""
    def _walk(start: Path) -> Path | None:
        for candidate in (start, *start.parents):
            if (candidate / ".git").exists() or (candidate / "validators").is_dir():
                return candidate
        return None

    primary = path if path.is_dir() else path.parent
    for start in (primary, Path.cwd(), Path(__file__).resolve().parent):
        found = _walk(start)
        if found is not None:
            return found
    return Path.cwd()


def _sha256_of_file(path: Path) -> str | None:
    try:
        with path.open("rb") as fh:
            hasher = hashlib.sha256()
            for chunk in iter(lambda: fh.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except OSError:
        return None


def _resolve_envelope(envelope_ref: str, repo_root: Path) -> Path | None:
    """Return the resolved envelope path if it points at an existing file."""
    if not isinstance(envelope_ref, str) or not envelope_ref:
        return None
    # Try repo-root-relative first; then CWD-relative. Skip when neither resolves.
    candidates = [repo_root / envelope_ref, Path.cwd() / envelope_ref, Path(envelope_ref)]
    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def _pair_envelope_for_report(
    report_path: Path,
    record: dict[str, Any],
    repo_root: Path,
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    envelope_ref = record.get("envelope_ref")
    declared_sha = record.get("envelope_sha256")
    if not isinstance(envelope_ref, str) or not isinstance(declared_sha, str):
        # Schema-shape errors are the responsibility of CR-001; CR-002
        # is silent on records that fail the schema's structural
        # requirements.
        return errors
    envelope_path = _resolve_envelope(envelope_ref, repo_root)
    if envelope_path is None:
        # Envelope likely lives under the local-runtime tree
        # (`.hermes/`); skip the active SHA check.
        return errors
    actual_sha = _sha256_of_file(envelope_path)
    if actual_sha is None:
        return errors
    if actual_sha != declared_sha.lower():
        errors.append(
            make_error(
                CODE_PAIRING,
                report_path,
                "/envelope_sha256",
                (
                    f"envelope_ref points at {envelope_ref!r} which exists on disk with SHA256 "
                    f"{actual_sha}, but envelope_sha256 declares {declared_sha}; the report does "
                    "not bind to the bytes Source ratified"
                ),
                CONTRACT,
            )
        )
    return errors


@register(CHECK_NAME, [CODE_PAIRING])
def run(paths: Iterable[Path]) -> CheckResult:
    raw_paths = [Path(p) for p in paths] or [Path(".")]
    repo_root = _repo_root_for(raw_paths[0])
    errors: list[ValidationError] = []
    envelope_to_completed_reports: dict[str, list[Path]] = {}
    for record_path in iter_completion_report_records(raw_paths):
        try:
            record = load_yaml(record_path)
        except LoaderError:
            continue
        if not isinstance(record, dict):
            continue
        errors.extend(_pair_envelope_for_report(record_path, record, repo_root))
        outcome = record.get("outcome")
        envelope_ref = record.get("envelope_ref")
        if outcome == "completed" and isinstance(envelope_ref, str):
            envelope_to_completed_reports.setdefault(envelope_ref, []).append(record_path)
    for envelope_ref, completed_reports in envelope_to_completed_reports.items():
        if len(completed_reports) > 1:
            rendered = ", ".join(sorted(str(p) for p in completed_reports))
            errors.append(
                make_error(
                    CODE_PAIRING,
                    completed_reports[0],
                    "/envelope_ref",
                    (
                        f"envelope_ref {envelope_ref!r} is referenced by more than one completion "
                        f"report with outcome=completed: {rendered}; at most one completed report "
                        "is permitted per ratified envelope"
                    ),
                    CONTRACT,
                )
            )
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
