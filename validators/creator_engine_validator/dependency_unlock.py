"""Merge-triggered dependency-unlock evaluator (slice 1, SHADOW-first).

This module implements the vocabulary of ``docs/contracts/dependency-unlock.md``
for exactly one re-evaluation event family: a pull request merging into
``main``. It never ratifies, approves, merges, dispatches, or bypasses a
required check. It only proposes the smallest readiness change described by
the contract -- removing a dependency-specific hold label once every declared
blocker is independently confirmed complete -- and, in SHADOW mode (the only
mode this module ships enabled), makes zero GitHub write calls.

GitHub I/O is reachable only through an injectable ``GhRunner`` seam; importing
this module performs no network or disk I/O.

Blocker-reference PARSING deliberately reuses (never reimplements) the shared
primitives already ratified for this purpose:

- ``forge_triage.readiness_blockers`` / ``forge_triage._BLOCKING_LABEL_PREFIXES``
  / ``forge_triage._DEPENDENCY_FIELDS`` classify *whether* an issue carries a
  dependency declaration.
- ``forge_triage._extract_issue_refs`` / ``forge_triage._DEPENDENCY_BODY_RE``
  supply the actual ref-matching regexes; this module only ever hands them
  text to match, never duplicates their patterns.

CLOSED-WITHOUT-MERGE RULE (verbatim, review-banked): closed-without-
merge is NOT completion; the blocker stays blocking unless a completed
successor is declared or the dependency is explicitly removed. Implemented as:
a pull-request blocker resolves iff ``merged is True``; an issue blocker
resolves iff ``state == "closed" and state_reason == "completed"``. Everything
else (closed unmerged, ``not_planned``, unknown, inaccessible) stays blocking,
fail-closed.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import urllib.parse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import forge_triage

GhRunner = Callable[[Sequence[str], "str | None"], subprocess.CompletedProcess]

SCHEMA_VERSION = 1
KIND = "ce-dependency-unlock-scan"
DEFAULT_SEARCH_REPO = "creator-engine/ce-ops"
NON_AUTHORITY_STATEMENT = (
    "This scan proposes a narrow readiness change only (removing a resolved "
    "dependency hold label). It does not ratify, approve, merge, dispatch, "
    "bypass a required check, or grant privileged action."
)

# Dependency-qualified hold labels per docs/contracts/dependency-unlock.md:
# "Dependency-qualified labels use the blocked:<blocker-ref> or
# blocked/<blocker-ref> family." Any OTHER blocking-family label present
# (bare "blocked"/"hold"/"wip"/..., or the checkpoint:/held:/hold: prefix
# families, or the AWAITING-OPERATOR family -- all reused verbatim from
# forge_triage/forge.hold_labels) is a non-dependency hold and keeps the item
# blocked even when every dependency is independently resolved.
_DEPENDENCY_HOLD_LABEL_PREFIXES = ("blocked:", "blocked/")

_RUN_MODE_LIVE = "live"
# Mirrors creator_engine_validator.forge.automerge_policy._truthy_variable's
# accepted truthy vocabulary, kept local so this module stays a self-contained
# validator (no cross-module coupling beyond forge_triage's blocker parsing).
_TRUTHY_VALUES = frozenset({"1", "true", "yes", "on", "kill", "halt"})

# Contract-defined dedup window; this slice only ever produces "instant"
# (one completed-work event / canonical payload) windows.
WINDOW = "instant"
NORMALIZED_EVENT_KIND = "pr_merged"


def _truthy(value: str | None) -> bool:
    return isinstance(value, str) and value.strip().lower() in _TRUTHY_VALUES


def resolve_apply_mode(
    *, run_mode: str | None, kill_switch: str | None
) -> tuple[bool, str]:
    """Resolve the (apply, mode-label) pair from the two repo-variable switches.

    ``CE_DEP_UNLOCK_KILL_SWITCH`` truthy FORCES shadow regardless of run mode.
    Otherwise ``CE_DEP_UNLOCK_RUN_MODE == "live"`` (case-insensitive) enables
    apply; anything else (including unset) stays shadow. Ships with neither
    variable set, i.e. shadow-only.
    """
    if _truthy(kill_switch):
        return False, "shadow"
    if str(run_mode or "").strip().lower() == _RUN_MODE_LIVE:
        return True, "live"
    return False, "shadow"


def default_gh_runner(
    argv: Sequence[str], input_text: str | None = None
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    cross_repo_token = env.get("CE_CROSS_REPO_TOKEN")
    if cross_repo_token and not env.get("GH_TOKEN"):
        env["GH_TOKEN"] = cross_repo_token
    return subprocess.run(
        list(argv),
        check=False,
        capture_output=True,
        text=True,
        input=input_text,
        timeout=60,
        env=env,
    )


@dataclass(frozen=True)
class BlockerRef:
    """One normalized blocker identity (``owner/name#number``)."""

    repo: str
    number: int

    @property
    def ref_key(self) -> str:
        return f"{self.repo.lower()}#{self.number}"

    def to_dict(self) -> dict[str, Any]:
        return {"repo": self.repo, "number": self.number}


@dataclass(frozen=True)
class MergedItem:
    """The merge-triggering item identity. This slice's trigger is always a PR."""

    repo: str
    number: int
    merge_sha: str
    merged_at: str

    @property
    def ref(self) -> BlockerRef:
        return BlockerRef(repo=self.repo, number=self.number)

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo,
            "number": self.number,
            "merge_sha": self.merge_sha,
            "merged_at": self.merged_at,
        }


@dataclass(frozen=True)
class BlockerResolution:
    """Live-resolved status for one declared blocker reference."""

    ref: BlockerRef
    kind: str  # "pr" | "issue" | "unknown"
    resolved: bool
    state: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ref": self.ref.to_dict(),
            "kind": self.kind,
            "resolved": self.resolved,
            "state": self.state,
        }


def merged_item_from_event(
    event: Mapping[str, Any], *, default_repo: str | None = None
) -> MergedItem | None:
    """Build a ``MergedItem`` from a GitHub ``pull_request`` webhook payload.

    Returns ``None`` (refusal, not best-effort) if the event is not a merged
    pull request or is missing required evidence (repo, number, merge SHA,
    merged-at timestamp). The ``base.ref == 'main'`` gate is enforced at the
    workflow ``if:`` level (mirrors ``ce-ops-autoclose.yml``); this function
    only re-asserts ``merged is True`` as defense in depth.
    """
    if not isinstance(event, Mapping):
        return None
    pr = event.get("pull_request")
    if not isinstance(pr, Mapping) or pr.get("merged") is not True:
        return None
    number = pr.get("number")
    repo = default_repo
    repository = event.get("repository")
    if isinstance(repository, Mapping) and isinstance(repository.get("full_name"), str):
        repo = repository["full_name"]
    merge_sha = pr.get("merge_commit_sha")
    merged_at = pr.get("merged_at")
    if not isinstance(repo, str) or not repo.strip():
        return None
    if not isinstance(number, int):
        return None
    if not isinstance(merge_sha, str) or not merge_sha.strip():
        return None
    if not isinstance(merged_at, str) or not merged_at.strip():
        return None
    return MergedItem(repo=repo.strip(), number=number, merge_sha=merge_sha.strip(), merged_at=merged_at.strip())


def search_dependency_candidates(
    merged: MergedItem,
    *,
    search_repo: str = DEFAULT_SEARCH_REPO,
    gh_runner: GhRunner,
) -> tuple[tuple[Any, ...], bool, str | None]:
    """Search ``search_repo`` open issues whose blocker surfaces might name ``merged``.

    Returns ``(raw_issues, ok, warning)``. ``ok is False`` means the
    cross-repo blocker-reference search itself is degraded or incomplete, and
    the caller MUST treat the whole scan as inconclusive (refuse, never
    silently partial) rather than act on whatever subset did return.

    Uses GitHub's exact ``label:`` search qualifier for the dependency-hold
    label family (precise) plus a free-text fallback for structured-field and
    body-line declarations (coarse net; every hit is re-verified against the
    freshly re-read issue before any decision is made, so over-matching here
    is safe).
    """
    ref = merged.ref
    queries: list[str] = [
        f'repo:{search_repo} is:issue is:open label:"blocked:{ref.repo}#{ref.number}"',
        f'repo:{search_repo} is:issue is:open label:"blocked/{ref.repo}#{ref.number}"',
        f'repo:{search_repo} is:issue is:open "{ref.repo}#{ref.number}"',
    ]
    if search_repo.lower() == ref.repo.lower():
        queries.append(f'repo:{search_repo} is:issue is:open label:"blocked:{ref.number}"')
        queries.append(f'repo:{search_repo} is:issue is:open label:"blocked/{ref.number}"')

    by_number: dict[int, Any] = {}
    for query in queries:
        code, payload, stderr = _gh_api(
            gh_runner,
            "search/issues?" + urllib.parse.urlencode({"q": query, "per_page": "100"}),
            method="GET",
        )
        if code != 0 or not isinstance(payload, Mapping):
            return (), False, f"search_failed:{stderr.strip() or code}"
        items = payload.get("items")
        if not isinstance(items, list):
            return (), False, "search_malformed"
        for raw in items:
            if isinstance(raw, Mapping):
                number = raw.get("number")
                if isinstance(number, int):
                    by_number.setdefault(number, raw)
    return tuple(by_number[number] for number in sorted(by_number)), True, None


def _dependency_hold_labels(labels: Sequence[str]) -> tuple[str, ...]:
    return tuple(
        label for label in labels if _label_key(label).startswith(_DEPENDENCY_HOLD_LABEL_PREFIXES)
    )


def _label_key(label: str) -> str:
    return str(label or "").strip().lower()


def _non_dependency_hold_present(labels: Sequence[str]) -> bool:
    keys = {_label_key(label) for label in labels}
    if keys.intersection(forge_triage._BLOCKING_LABELS):
        return True
    for label in labels:
        key = _label_key(label)
        if key.startswith(_DEPENDENCY_HOLD_LABEL_PREFIXES):
            continue
        if key.startswith(forge_triage._BLOCKING_LABEL_PREFIXES):
            return True
    return False


# A bare trailing digit run (no leading "#", no owner/repo, no URL) still
# counts as a body/structured-field blocker reference per the contract's
# markdown-dependency-line example set ("Blocked by: 123"). This is the ONLY
# local normalization this module performs before delegating to
# ``forge_triage._extract_issue_refs``: it never re-implements ref matching,
# it only makes a bare number look like the ``#123`` form that
# ``_extract_issue_refs`` already parses.
_TRAILING_BARE_NUMBER_RE = re.compile(r"(?<![#/\w])(\d+)\s*$")


def _normalize_bare_trailing_number(text: str) -> str:
    if "#" in text or "http" in text.lower():
        return text
    match = _TRAILING_BARE_NUMBER_RE.search(text)
    if not match:
        return text
    start, _end = match.span(1)
    return text[:start] + "#" + text[start:]


def _parse_ref_token(token: str, *, default_repo: str) -> tuple[BlockerRef | None, bool]:
    """Parse one blocker-reference token into exactly one ``BlockerRef``.

    Returns ``(ref, ambiguous)``. ``ref is None`` means the token is
    unparseable (fail-closed). ``ambiguous`` is ``True`` when the token
    resolves to more than one distinct ``(repo, number)`` pair (fail-closed:
    "a blocker reference cannot be resolved to exactly one item"). All actual
    pattern matching is delegated to ``forge_triage._extract_issue_refs``.
    """
    text = str(token or "").strip()
    if not text:
        return None, False
    normalized = _normalize_bare_trailing_number(text)
    refs_map = forge_triage._extract_issue_refs(normalized, default_repo)
    pairs = [(repo, number) for repo, numbers in refs_map.items() for number in sorted(numbers)]
    if len(pairs) != 1:
        return None, len(pairs) > 1
    repo, number = pairs[0]
    return BlockerRef(repo=repo, number=number), False


@dataclass(frozen=True)
class DeclaredBlockers:
    refs: tuple[BlockerRef, ...]
    problems: tuple[str, ...]


def declared_blockers(candidate: forge_triage.IssueCandidate) -> DeclaredBlockers:
    """Union every declared blocker reference across all three contract surfaces.

    Reuses (never reimplements): dependency-hold label detection via
    ``_DEPENDENCY_HOLD_LABEL_PREFIXES`` (the contract's ``blocked:``/``blocked/``
    family), ``forge_triage._DEPENDENCY_FIELDS`` for structured fields, and
    ``forge_triage._DEPENDENCY_BODY_RE`` for markdown dependency lines.
    """
    refs: list[BlockerRef] = []
    problems: list[str] = []

    for label in _dependency_hold_labels(candidate.labels):
        key = _label_key(label)
        for prefix in _DEPENDENCY_HOLD_LABEL_PREFIXES:
            if key.startswith(prefix):
                suffix = label.strip()[len(prefix) :]
                break
        else:  # pragma: no cover - unreachable, label already prefix-filtered
            suffix = ""
        ref, ambiguous = _parse_ref_token(suffix, default_repo=candidate.repo)
        if ref is None:
            problems.append("ambiguous_blocker_ref" if ambiguous else "unparseable_blocker_ref")
            continue
        refs.append(ref)

    raw = candidate.raw or {}
    if isinstance(raw, Mapping):
        for field in forge_triage._DEPENDENCY_FIELDS:
            value = raw.get(field)
            if not forge_triage._non_empty_dependency_value(value):
                continue
            for token in forge_triage._string_tuple(value):
                ref, ambiguous = _parse_ref_token(token, default_repo=candidate.repo)
                if ref is None:
                    problems.append("ambiguous_blocker_ref" if ambiguous else "unparseable_blocker_ref")
                    continue
                refs.append(ref)

    for match in forge_triage._DEPENDENCY_BODY_RE.finditer(candidate.body):
        ref, ambiguous = _parse_ref_token(match.group(0), default_repo=candidate.repo)
        if ref is None:
            problems.append("ambiguous_blocker_ref" if ambiguous else "unparseable_blocker_ref")
            continue
        refs.append(ref)

    deduped: list[BlockerRef] = []
    seen: set[str] = set()
    for ref in refs:
        if ref.ref_key not in seen:
            seen.add(ref.ref_key)
            deduped.append(ref)
    return DeclaredBlockers(refs=tuple(deduped), problems=tuple(_dedupe_strings(problems)))


def _dedupe_strings(values: Sequence[str]) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return tuple(out)


def _fetch_issue(repo: str, number: int, gh_runner: GhRunner) -> Mapping[str, Any] | None:
    code, payload, _stderr = _gh_api(gh_runner, f"repos/{repo}/issues/{number}", method="GET")
    if code != 0 or not isinstance(payload, Mapping):
        return None
    return payload


def _fetch_pull(repo: str, number: int, gh_runner: GhRunner) -> Mapping[str, Any] | None:
    code, payload, _stderr = _gh_api(gh_runner, f"repos/{repo}/pulls/{number}", method="GET")
    if code != 0 or not isinstance(payload, Mapping):
        return None
    return payload


def resolve_blocker(
    ref: BlockerRef, *, merged: MergedItem, gh_runner: GhRunner
) -> BlockerResolution:
    """Resolve one blocker reference's live completion state, fail-closed.

    CLOSED-WITHOUT-MERGE RULE: a PR blocker resolves iff ``merged is True``;
    an issue blocker resolves iff ``state == "closed" and
    state_reason == "completed"``. Any inaccessible/unknown/ambiguous read
    stays unresolved (blocking).
    """
    if ref == merged.ref:
        # The triggering event already carries authoritative merged evidence;
        # no extra API round trip needed for the item that fired this run.
        return BlockerResolution(ref=ref, kind="pr", resolved=True, state="merged")

    issue_payload = _fetch_issue(ref.repo, ref.number, gh_runner)
    if issue_payload is None:
        return BlockerResolution(ref=ref, kind="unknown", resolved=False, state="inaccessible")

    if issue_payload.get("pull_request") is not None:
        pull_payload = _fetch_pull(ref.repo, ref.number, gh_runner)
        if pull_payload is None:
            return BlockerResolution(ref=ref, kind="pr", resolved=False, state="inaccessible")
        if pull_payload.get("merged") is True:
            return BlockerResolution(ref=ref, kind="pr", resolved=True, state="merged")
        state = str(pull_payload.get("state") or "").strip().lower()
        return BlockerResolution(
            ref=ref,
            kind="pr",
            resolved=False,
            state="closed_unmerged" if state == "closed" else "open",
        )

    state = str(issue_payload.get("state") or "").strip().lower()
    state_reason = issue_payload.get("state_reason")
    if state == "closed" and state_reason == "completed":
        return BlockerResolution(ref=ref, kind="issue", resolved=True, state="closed_completed")
    if state == "closed":
        return BlockerResolution(
            ref=ref,
            kind="issue",
            resolved=False,
            state="closed_not_planned" if state_reason == "not_planned" else "closed_unspecified_reason",
        )
    return BlockerResolution(ref=ref, kind="issue", resolved=False, state="open")


def _evidence_hash(
    *, candidate_repo: str, candidate_number: int, labels: Sequence[str], resolutions: Sequence[BlockerResolution]
) -> str:
    payload = {
        "repo": candidate_repo,
        "number": candidate_number,
        "labels": sorted({_label_key(label) for label in labels}),
        "blockers": sorted(f"{r.ref.ref_key}:{r.state}" for r in resolutions),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _dedup_key(
    *, candidate_repo: str, candidate_number: int, blocker_ref: BlockerRef, evidence_hash: str
) -> str:
    return "|".join(
        [
            "dependency_unlock",
            candidate_repo,
            f"{candidate_repo}#{candidate_number}",
            blocker_ref.ref_key,
            NORMALIZED_EVENT_KIND,
            evidence_hash,
            WINDOW,
        ]
    )


def _evaluate_one_candidate(
    raw: Any,
    *,
    merged: MergedItem,
    search_repo: str,
    apply: bool,
    gh_runner: GhRunner,
) -> dict[str, Any]:
    candidate = forge_triage.normalize_issue(raw, default_repo=search_repo)
    if candidate is None:
        return {"status": "skipped", "reason": "unparseable_search_result"}

    fresh_payload = _fetch_issue(candidate.repo, candidate.number, gh_runner)
    if fresh_payload is None:
        return {
            "status": "blocked",
            "reason": "reread_failed",
            "candidate": {"repo": candidate.repo, "number": candidate.number},
        }
    fresh = forge_triage.normalize_issue(fresh_payload, default_repo=search_repo)
    if fresh is None:
        return {
            "status": "blocked",
            "reason": "reread_failed",
            "candidate": {"repo": candidate.repo, "number": candidate.number},
        }
    if fresh.state.strip().lower() != "open":
        return {
            "status": "skipped",
            "reason": "candidate_not_open",
            "candidate": {"repo": fresh.repo, "number": fresh.number},
        }

    declared = declared_blockers(fresh)
    if merged.ref.ref_key not in {ref.ref_key for ref in declared.refs}:
        return {
            "status": "skipped",
            "reason": "not_a_declared_blocker",
            "candidate": {"repo": fresh.repo, "number": fresh.number},
        }

    base_report: dict[str, Any] = {
        "candidate": {"repo": fresh.repo, "number": fresh.number, "title": fresh.title},
        "declared_blockers": [ref.to_dict() for ref in declared.refs],
    }

    if declared.problems:
        base_report["status"] = "blocked"
        base_report["reason"] = declared.problems[0]
        base_report["problems"] = list(declared.problems)
        return base_report

    resolutions = tuple(resolve_blocker(ref, merged=merged, gh_runner=gh_runner) for ref in declared.refs)
    base_report["blocker_resolutions"] = [r.to_dict() for r in resolutions]
    unresolved = [r for r in resolutions if not r.resolved]
    if unresolved:
        base_report["status"] = "blocked"
        base_report["reason"] = "blocker_unresolved"
        return base_report

    if _non_dependency_hold_present(fresh.labels):
        base_report["status"] = "blocked"
        base_report["reason"] = "non_dependency_hold_present"
        return base_report

    labels_to_remove = _dependency_hold_labels(fresh.labels)
    if not labels_to_remove:
        base_report["status"] = "blocked"
        base_report["reason"] = "no_dependency_hold_label_present"
        return base_report

    evidence_hash = _evidence_hash(
        candidate_repo=fresh.repo,
        candidate_number=fresh.number,
        labels=fresh.labels,
        resolutions=resolutions,
    )
    dedup_key = _dedup_key(
        candidate_repo=fresh.repo,
        candidate_number=fresh.number,
        blocker_ref=merged.ref,
        evidence_hash=evidence_hash,
    )
    proposal: dict[str, Any] = {
        "candidate_repo": fresh.repo,
        "candidate_number": fresh.number,
        "blocker_refs": [ref.to_dict() for ref in declared.refs],
        "labels_to_remove": list(labels_to_remove),
        "dedup_key": dedup_key,
        "evidence_hash": evidence_hash,
        "status": "proposed",
        "applied": False,
    }

    if apply:
        proposal.update(
            _apply_unlock(
                repo=fresh.repo,
                number=fresh.number,
                labels_to_remove=labels_to_remove,
                merged=merged,
                expected_blocker_refs=declared.refs,
                expected_evidence_hash=evidence_hash,
                gh_runner=gh_runner,
            )
        )

    base_report["status"] = "proposed"
    base_report["proposal"] = proposal
    return base_report


def _apply_unlock(
    *,
    repo: str,
    number: int,
    labels_to_remove: Sequence[str],
    gh_runner: GhRunner,
    merged: MergedItem,
    expected_blocker_refs: Sequence[BlockerRef],
    expected_evidence_hash: str,
) -> dict[str, Any]:
    """LIVE-mode mutation (dormant this slice): remove each resolved dependency-hold label.

    Re-checks the live candidate immediately before mutating (stale-evidence
    guard: "if the mutation target changed after evidence was computed, the
    candidate is stale and must be re-evaluated").
    """
    recheck_payload = _fetch_issue(repo, number, gh_runner)
    if recheck_payload is None:
        return {"applied": False, "warning": "recheck_failed"}
    recheck_candidate = forge_triage.normalize_issue(recheck_payload, default_repo=repo)
    if recheck_candidate is None:
        return {"applied": False, "warning": "recheck_failed"}
    if recheck_candidate.state.strip().lower() != "open":
        return _stale_apply_refusal(
            "candidate_not_open_at_apply",
            candidate=recheck_candidate,
            expected_evidence_hash=expected_evidence_hash,
        )

    declared = declared_blockers(recheck_candidate)
    if declared.problems:
        return _stale_apply_refusal(
            declared.problems[0],
            candidate=recheck_candidate,
            expected_evidence_hash=expected_evidence_hash,
            problems=declared.problems,
        )
    expected_ref_keys = {ref.ref_key for ref in expected_blocker_refs}
    actual_ref_keys = {ref.ref_key for ref in declared.refs}
    if actual_ref_keys != expected_ref_keys:
        return _stale_apply_refusal(
            "declared_blockers_changed_at_apply",
            candidate=recheck_candidate,
            expected_evidence_hash=expected_evidence_hash,
            declared_blockers=declared.refs,
        )

    resolutions = tuple(resolve_blocker(ref, merged=merged, gh_runner=gh_runner) for ref in declared.refs)
    unresolved = [resolution for resolution in resolutions if not resolution.resolved]
    if unresolved:
        return _stale_apply_refusal(
            "blocker_unresolved_at_apply",
            candidate=recheck_candidate,
            expected_evidence_hash=expected_evidence_hash,
            declared_blockers=declared.refs,
            blocker_resolutions=resolutions,
        )
    if _non_dependency_hold_present(recheck_candidate.labels):
        # A non-dependency hold label appeared since evidence was computed:
        # the mutation target is stale. Re-evaluate on the next run rather
        # than partially applying against changed state.
        return _stale_apply_refusal(
            "non_dependency_hold_present_at_apply",
            candidate=recheck_candidate,
            expected_evidence_hash=expected_evidence_hash,
            declared_blockers=declared.refs,
            blocker_resolutions=resolutions,
        )

    recheck_evidence_hash = _evidence_hash(
        candidate_repo=recheck_candidate.repo,
        candidate_number=recheck_candidate.number,
        labels=recheck_candidate.labels,
        resolutions=resolutions,
    )
    if recheck_evidence_hash != expected_evidence_hash:
        return _stale_apply_refusal(
            "evidence_changed_at_apply",
            candidate=recheck_candidate,
            expected_evidence_hash=expected_evidence_hash,
            actual_evidence_hash=recheck_evidence_hash,
            declared_blockers=declared.refs,
            blocker_resolutions=resolutions,
        )
    current = {_label_key(label) for label in recheck_candidate.labels}

    removed: list[str] = []
    errors: list[str] = []
    for label in labels_to_remove:
        if _label_key(label) not in current:
            removed.append(label)  # already absent: success no-op
            continue
        ok, detail = _remove_issue_label(repo, number, label, gh_runner=gh_runner)
        if ok:
            removed.append(label)
        else:
            errors.append(f"{label}:{detail}")
    if errors:
        return {"applied": False, "removed": removed, "warning": f"remove_failed:{';'.join(errors)}"}
    return {"applied": True, "removed": removed}


def _stale_apply_refusal(
    reason: str,
    *,
    candidate: forge_triage.IssueCandidate,
    expected_evidence_hash: str,
    actual_evidence_hash: str | None = None,
    declared_blockers: Sequence[BlockerRef] = (),
    blocker_resolutions: Sequence[BlockerResolution] = (),
    problems: Sequence[str] = (),
) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "candidate": {
            "repo": candidate.repo,
            "number": candidate.number,
            "state": candidate.state,
            "labels": list(candidate.labels),
        },
        "expected_evidence_hash": expected_evidence_hash,
    }
    if actual_evidence_hash is not None:
        evidence["actual_evidence_hash"] = actual_evidence_hash
    if declared_blockers:
        evidence["declared_blockers"] = [ref.to_dict() for ref in declared_blockers]
    if blocker_resolutions:
        evidence["blocker_resolutions"] = [resolution.to_dict() for resolution in blocker_resolutions]
    if problems:
        evidence["problems"] = list(problems)
    return {
        "applied": False,
        "warning": "stale_mutation_target",
        "refusal_reason": reason,
        "refusal_evidence": evidence,
    }


def _remove_issue_label(
    repo: str, issue_number: int, label: str, *, gh_runner: GhRunner
) -> tuple[bool, str]:
    code, _payload, stderr = _gh_api(
        gh_runner,
        f"repos/{repo}/issues/{issue_number}/labels/{urllib.parse.quote(label, safe='')}",
        method="DELETE",
    )
    if code == 0:
        return True, ""
    # A 404 (label already gone) is a success no-op, not a failure.
    if "404" in stderr or "Not Found" in stderr or "not found" in stderr:
        return True, ""
    return False, stderr.strip() or str(code)


def evaluate_pr_merge(
    merged: MergedItem,
    *,
    search_repo: str = DEFAULT_SEARCH_REPO,
    run_mode: str | None = None,
    kill_switch: str | None = None,
    gh_runner: GhRunner | None = None,
    audit_root: str | Path | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Evaluate one merged-PR event against every declared blocker it might resolve.

    Pure orchestration: search -> re-read each candidate fresh -> recompute
    declared blockers -> resolve every blocker live -> propose (SHADOW: log
    only; LIVE: dormant re-checked mutation) or refuse/stay-blocked. Always
    writes an audit record when ``audit_root`` is given, on every code path.
    """
    runner = gh_runner or default_gh_runner
    evaluated_at = now or utc_now_iso()
    apply, mode = resolve_apply_mode(run_mode=run_mode, kill_switch=kill_switch)

    result: dict[str, Any] = {
        "kind": KIND,
        "schema_version": SCHEMA_VERSION,
        "advisory": NON_AUTHORITY_STATEMENT,
        "mode": mode,
        "apply_requested": apply,
        "merged_item": merged.to_dict(),
        "search_repo": search_repo,
        "evaluated_at": evaluated_at,
        "warnings": [],
    }

    if not _cross_repo_token_present():
        result.update(
            {
                "status": "refused",
                "refusal_reason": "cross_repo_token_absent",
                "credential_evidence": {
                    "required_env": "CE_CROSS_REPO_TOKEN",
                    "present": False,
                },
                "search_ok": False,
                "candidate_count": 0,
                "proposal_count": 0,
                "proposals": [],
            }
        )
        result["warnings"].append("cross_repo_token_absent")
        write_audit_record(audit_root, result, evaluated_at=evaluated_at)
        return result

    raw_candidates, search_ok, search_warning = search_dependency_candidates(
        merged, search_repo=search_repo, gh_runner=runner
    )
    result["search_ok"] = search_ok
    if not search_ok:
        result["status"] = "refused"
        result["refusal_reason"] = "search_inconclusive"
        result["candidate_count"] = 0
        result["proposal_count"] = 0
        result["proposals"] = []
        result["warnings"].append(search_warning or "search_inconclusive")
        write_audit_record(audit_root, result, evaluated_at=evaluated_at)
        return result

    candidate_reports: list[dict[str, Any]] = []
    proposals: list[dict[str, Any]] = []
    for raw in raw_candidates:
        report = _evaluate_one_candidate(
            raw, merged=merged, search_repo=search_repo, apply=apply, gh_runner=runner
        )
        candidate_reports.append(report)
        proposal = report.get("proposal")
        if proposal is not None:
            proposals.append(proposal)

    result["candidates"] = candidate_reports
    result["candidate_count"] = len(candidate_reports)
    result["proposals"] = proposals
    result["proposal_count"] = len(proposals)
    result["status"] = "ok"
    write_audit_record(audit_root, result, evaluated_at=evaluated_at)
    return result


def _cross_repo_token_present() -> bool:
    return bool(os.environ.get("CE_CROSS_REPO_TOKEN", "").strip())


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_audit_record(
    audit_root: str | Path | None, record: Mapping[str, Any], *, evaluated_at: str
) -> Path | None:
    if audit_root is None:
        return None
    root = Path(audit_root)
    root.mkdir(parents=True, exist_ok=True)
    stamp = _safe_stamp(evaluated_at)
    path = root / f"ce-dependency-unlock-{stamp}.json"
    payload = dict(record)
    payload.setdefault("advisory", NON_AUTHORITY_STATEMENT)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _safe_stamp(value: str) -> str:
    return "".join(char if char.isalnum() else "-" for char in value).strip("-")


def _gh_api(
    runner: GhRunner,
    path: str,
    *,
    method: str | None = None,
    body: Mapping[str, Any] | None = None,
) -> tuple[int, object, str]:
    argv: list[str] = ["gh", "api"]
    if method is not None:
        argv += ["--method", method]
    argv.append(path)
    input_text: str | None = None
    if body is not None:
        argv += ["--input", "-"]
        input_text = json.dumps(dict(body))
    try:
        proc = runner(argv, input_text)
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, None, str(exc)
    out = (getattr(proc, "stdout", "") or "").strip()
    parsed: object = None
    if out:
        try:
            parsed = json.loads(out)
        except (json.JSONDecodeError, ValueError):
            parsed = None
    return int(getattr(proc, "returncode", 1)), parsed, getattr(proc, "stderr", "") or ""
