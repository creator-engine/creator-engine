"""Fail-closed current-head coupling evidence for automerge actuation.

The existing validators remain the authority for each individual coupling.  This
module binds their *decision-time input set* to the live PR immediately before
the actuator can mutate.  It is deliberately value-only: it has no merge,
review, workflow, or ruleset authority.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final


COUPLING_GATE_ID: Final[str] = "ce.coupling-current-head"
COUPLING_GATE_VERSION: Final[int] = 1
_SHA_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{40}$")
_REPO_RE: Final[re.Pattern[str]] = re.compile(r"^[^/\s]+/[^/\s]+$")

# These are seed *kinds*, rather than a closed list of paths.  Each obligation
# binds the exact target head and deterministic subject projection; individual
# validators continue to establish the semantic property itself.
SEED_KINDS: Final[tuple[str, ...]] = (
    "brain.evidence_current",
    "generated.schema_reference",
    "generated.cli_reference",
    "confidentiality.tracked_text",
    "carrier.slug_identity",
    "carrier.closed_pathset",
    "brain.required_semantics",
)


@dataclass(frozen=True)
class CouplingVerification:
    """Secret-free result for pre-mutation current-head verification."""

    status: str
    reason: str
    drifted_kinds: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == "PASS"


def canonical_paths_digest(paths: Sequence[str]) -> str:
    """Hash the canonical, duplicate-free current diff path projection."""

    normalized = _normalized_paths(paths)
    return hashlib.sha256("\n".join(normalized).encode("utf-8") + b"\n").hexdigest()


def build_obligation_set(
    *,
    repo: str | None,
    pr_number: int | None,
    base: str | None,
    head: str | None,
    branch: str | None,
    paths: Sequence[str] | None,
) -> dict[str, Any] | None:
    """Build a deterministic decision snapshot, or ``None`` when incomplete.

    A branch name is retained for carrier-slug identity.  The base and head are
    immutable object IDs; accepting a mutable ref here would leave a stale
    decision capable of being replayed after its comparison changed.
    """

    if (
        not isinstance(repo, str)
        or not _REPO_RE.fullmatch(repo)
        or not isinstance(pr_number, int)
        or isinstance(pr_number, bool)
        or pr_number <= 0
        or not _sha(base)
        or not _sha(head)
        or not isinstance(branch, str)
        or not branch.strip()
        or paths is None
    ):
        return None
    try:
        normalized_paths = _normalized_paths(paths)
    except ValueError:
        return None

    subject = {
        "repo": repo,
        "pr_number": pr_number,
        "base_sha": base,
        "head_sha": head,
        "head_ref": branch.strip(),
        "paths_sha256": canonical_paths_digest(normalized_paths),
    }
    obligations = [
        {
            "id": kind,
            "kind": kind,
            "version": 1,
            "subject": _subject_projection(kind, subject),
        }
        for kind in SEED_KINDS
    ]
    result: dict[str, Any] = {
        "gate_id": COUPLING_GATE_ID,
        "version": COUPLING_GATE_VERSION,
        "subject": subject,
        "obligations": obligations,
    }
    result["obligation_set_sha256"] = _canonical_digest(result)
    return result


def verify_obligation_set(
    expected: Any,
    current: Any,
) -> CouplingVerification:
    """Compare complete obligation envelopes and name every drifted kind."""

    expected_parsed = _parse_obligation_set(expected)
    current_parsed = _parse_obligation_set(current)
    if expected_parsed is None or current_parsed is None:
        return CouplingVerification("INDETERMINATE", "obligation_set_invalid")

    if expected_parsed["subject"] != current_parsed["subject"]:
        # Exact subject binding is foundational.  Still report all kinds so a
        # human can distinguish head/base/ref drift from a partial set drift.
        return CouplingVerification("DRIFT", "subject_drift", SEED_KINDS)

    expected_by_kind = _obligations_by_kind(expected_parsed["obligations"])
    current_by_kind = _obligations_by_kind(current_parsed["obligations"])
    if expected_by_kind is None or current_by_kind is None:
        return CouplingVerification("INDETERMINATE", "obligation_kinds_invalid")
    drifted = tuple(
        kind
        for kind in SEED_KINDS
        if expected_by_kind.get(kind) != current_by_kind.get(kind)
    )
    if drifted:
        return CouplingVerification("DRIFT", "obligation_drift", drifted)
    return CouplingVerification("PASS", "current_head_matches")


def rederive_live_obligation_set(
    expected: Any,
    *,
    gh_runner,
) -> tuple[dict[str, Any] | None, str | None]:
    """Refetch the PR and derive obligations from its current remote subject."""

    parsed = _parse_obligation_set(expected)
    if parsed is None:
        return None, "obligation_set_invalid"
    subject = parsed["subject"]
    try:
        view = gh_runner(
            [
                "gh", "pr", "view", str(subject["pr_number"]), "--repo", subject["repo"],
                "--json", "headRefOid,baseRefOid,headRefName",
            ],
            None,
        )
    except Exception:
        return None, "live_subject_unreadable"
    if getattr(view, "returncode", 1) != 0:
        return None, "live_subject_unreadable"
    try:
        live = json.loads((getattr(view, "stdout", "") or "").strip() or "{}")
    except (json.JSONDecodeError, TypeError, ValueError):
        return None, "live_subject_unparseable"
    if not isinstance(live, Mapping):
        return None, "live_subject_unparseable"
    head = live.get("headRefOid")
    base = live.get("baseRefOid")
    branch = live.get("headRefName")
    if not _sha(head) or not _sha(base) or not isinstance(branch, str) or not branch.strip():
        return None, "live_subject_incomplete"

    try:
        diff = gh_runner(
            ["gh", "pr", "diff", str(subject["pr_number"]), "--repo", subject["repo"], "--name-only"],
            None,
        )
    except Exception:
        return None, "live_diff_unreadable"
    if getattr(diff, "returncode", 1) != 0:
        return None, "live_diff_unreadable"
    paths = (getattr(diff, "stdout", "") or "").splitlines()
    current = build_obligation_set(
        repo=subject["repo"],
        pr_number=subject["pr_number"],
        base=base,
        head=head,
        branch=branch,
        paths=paths,
    )
    if current is None:
        return None, "live_obligation_derivation_failed"
    return current, None


def verify_live_current_head(expected: Any, *, gh_runner) -> CouplingVerification:
    """Return PASS only when a complete live re-derivation equals the decision."""

    current, error = rederive_live_obligation_set(expected, gh_runner=gh_runner)
    if error is not None:
        return CouplingVerification("INDETERMINATE", error)
    return verify_obligation_set(expected, current)


def _parse_obligation_set(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    if value.get("gate_id") != COUPLING_GATE_ID or value.get("version") != COUPLING_GATE_VERSION:
        return None
    subject = value.get("subject")
    obligations = value.get("obligations")
    digest = value.get("obligation_set_sha256")
    if not isinstance(subject, Mapping) or not isinstance(obligations, Sequence) or isinstance(obligations, (str, bytes)):
        return None
    # The envelope retains the path digest, not its potentially very large raw
    # path list.  Validate the immutable subject shape and canonical envelope
    # digest instead; live re-derivation supplies the current raw path list.
    if not _valid_subject(subject) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        return None
    copied = {"gate_id": value.get("gate_id"), "version": value.get("version"), "subject": dict(subject), "obligations": list(obligations)}
    if _canonical_digest(copied) != digest:
        return None
    if _obligations_by_kind(copied["obligations"]) is None:
        return None
    return copied


def _valid_subject(subject: Mapping[str, Any]) -> bool:
    return (
        isinstance(subject.get("repo"), str)
        and bool(_REPO_RE.fullmatch(subject["repo"]))
        and isinstance(subject.get("pr_number"), int)
        and not isinstance(subject.get("pr_number"), bool)
        and subject["pr_number"] > 0
        and _sha(subject.get("base_sha"))
        and _sha(subject.get("head_sha"))
        and isinstance(subject.get("head_ref"), str)
        and bool(subject["head_ref"].strip())
        and isinstance(subject.get("paths_sha256"), str)
        and bool(re.fullmatch(r"[0-9a-f]{64}", subject["paths_sha256"]))
    )


def _obligations_by_kind(obligations: Sequence[Any]) -> dict[str, Any] | None:
    if len(obligations) != len(SEED_KINDS):
        return None
    parsed: dict[str, Any] = {}
    for obligation in obligations:
        if not isinstance(obligation, Mapping):
            return None
        kind = obligation.get("kind")
        if kind not in SEED_KINDS or obligation.get("id") != kind or obligation.get("version") != 1:
            return None
        if kind in parsed or not isinstance(obligation.get("subject"), Mapping):
            return None
        parsed[kind] = {"id": kind, "kind": kind, "version": 1, "subject": dict(obligation["subject"])}
    return parsed if tuple(parsed) == SEED_KINDS else None


def _subject_projection(kind: str, subject: Mapping[str, Any]) -> dict[str, Any]:
    common = {key: subject[key] for key in ("repo", "pr_number", "base_sha", "head_sha")}
    if kind == "carrier.slug_identity":
        return {**common, "head_ref": subject["head_ref"], "paths_sha256": subject["paths_sha256"]}
    if kind == "carrier.closed_pathset":
        return {**common, "paths_sha256": subject["paths_sha256"]}
    return {**common, "paths_sha256": subject["paths_sha256"]}


def _normalized_paths(paths: Sequence[str]) -> tuple[str, ...]:
    if isinstance(paths, (str, bytes)):
        raise ValueError("paths must be a sequence")
    normalized: set[str] = set()
    for path in paths:
        if not isinstance(path, str) or not path.strip() or "\n" in path or "\x00" in path:
            raise ValueError("path is invalid")
        normalized.add(path.strip())
    return tuple(sorted(normalized))


def _canonical_digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _sha(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA_RE.fullmatch(value))


__all__ = [
    "COUPLING_GATE_ID", "COUPLING_GATE_VERSION", "SEED_KINDS", "CouplingVerification",
    "build_obligation_set", "canonical_paths_digest", "rederive_live_obligation_set",
    "verify_live_current_head", "verify_obligation_set",
]
