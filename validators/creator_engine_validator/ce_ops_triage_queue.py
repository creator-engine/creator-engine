"""Advisory ce-ops issue triage queue.

This module scans recently updated open issues in ``creator-engine/ce-ops``,
classifies them with the existing forge triage primitives, and plans or applies
an advisory Markdown queue comment update. It does not ratify, approve, merge,
dispatch, or block CI. GitHub I/O is reachable only through an injectable
``GhRunner`` seam; importing this module performs no network or disk I/O.
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.parse
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from . import forge_triage
from .forge.controller_inbox import AWAITING_OPERATOR_LABELS

QUEUE_SENTINEL = "<!-- ce-triage-queue-issue:v1 -->"
NON_AUTHORITY_STATEMENT = (
    "Advisory only: this queue does not ratify, approve, review, merge, "
    "authorize dispatch, or block CI."
)
DEFAULT_REPO = "creator-engine/ce-ops"
DEFAULT_QUEUE_ISSUE = 67
DEFAULT_UPDATED_HOURS = 24
SCHEMA_VERSION = 1

GhRunner = Callable[[Sequence[str], "str | None"], subprocess.CompletedProcess]

WORK_CLASS_LABELS = frozenset({"wc:XS", "wc:S", "wc:M", "wc:L"})
READINESS_LABELS = frozenset({"triage:ready", "triage:blocked"})
MANAGED_LABEL_PREFIXES = ("wc:", "triage:")
MISSING_LABEL_POLICY = "create_missing"
PICKUP_IN_PROGRESS_LABELS = frozenset(
    {
        "assigned",
        "claimed",
        "in progress",
        "in-progress",
        "in_progress",
        "running",
        "status:assigned",
        "status:claimed",
        "status:in progress",
        "status:in-progress",
        "status:in_progress",
        "status:running",
        "status/assigned",
        "status/claimed",
        "status/in progress",
        "status/in-progress",
        "status/in_progress",
        "status/running",
    }
)
PICKUP_IN_PROGRESS_LABEL_PREFIXES = (
    "assigned:",
    "assigned/",
    "claimed:",
    "claimed/",
    "in-progress:",
    "in-progress/",
    "in_progress:",
    "in_progress/",
    "status:assigned:",
    "status:assigned/",
    "status:claimed:",
    "status:claimed/",
    "status:in-progress:",
    "status:in-progress/",
    "status:in_progress:",
    "status:in_progress/",
    "status:running:",
    "status:running/",
)
LABEL_SPECS: Mapping[str, Mapping[str, str]] = {
    "wc:XS": {
        "color": "c2e0c6",
        "description": "Advisory CE triage work-class classification: XS.",
    },
    "wc:S": {
        "color": "bfdadc",
        "description": "Advisory CE triage work-class classification: S.",
    },
    "wc:M": {
        "color": "fef2c0",
        "description": "Advisory CE triage work-class classification: M.",
    },
    "wc:L": {
        "color": "d93f0b",
        "description": "Advisory CE triage work-class classification: L.",
    },
    "triage:ready": {
        "color": "0e8a16",
        "description": "Advisory CE triage readiness classification: ready.",
    },
    "triage:blocked": {
        "color": "d93f0b",
        "description": "Advisory CE triage readiness classification: blocked.",
    },
}

LANE_LABEL_MAP: Mapping[str, str] = {
    "lane:l1": "L1",
    "lane/l1": "L1",
    "l1": "L1",
    "lane:l2": "L2",
    "lane/l2": "L2",
    "l2": "L2",
    "lane:l3": "L3",
    "lane/l3": "L3",
    "l3": "L3",
    "lane:l4": "L4",
    "lane/l4": "L4",
    "l4": "L4",
    "lane:l5": "L5",
    "lane/l5": "L5",
    "l5": "L5",
    "lane:l6": "L6",
    "lane/l6": "L6",
    "l6": "L6",
    "lane:l7": "L7",
    "lane/l7": "L7",
    "l7": "L7",
    "lane:l8": "L8",
    "lane/l8": "L8",
    "l8": "L8",
    "lane:l9": "L9",
    "lane/l9": "L9",
    "l9": "L9",
    "lane:l10": "L10",
    "lane/l10": "L10",
    "l10": "L10",
}


@dataclass(frozen=True)
class QueueEntry:
    issue_number: int
    repo: str
    title: str
    work_class: str
    mutation_class: str
    lane: str
    readiness: str
    blockers: tuple[str, ...]
    triaged_at: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["blockers"] = list(self.blockers)
        return payload


@dataclass(frozen=True)
class LabelDelta:
    issue_number: int
    repo: str
    current_managed: tuple[str, ...]
    desired: tuple[str, ...]
    add: tuple[str, ...]
    remove: tuple[str, ...]
    applied: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["current_managed"] = list(self.current_managed)
        payload["desired"] = list(self.desired)
        payload["add"] = list(self.add)
        payload["remove"] = list(self.remove)
        if self.error is None:
            payload.pop("error")
        return payload


@dataclass(frozen=True)
class PickupCandidate:
    """One advisory ready-to-dispatch candidate.

    Security note: ``labels`` is untrusted text sourced verbatim from the
    upstream issue. Consumers must never interpolate it into a shell command,
    branch name, or filesystem path without independent sanitization.
    """

    issue_number: int
    repo: str
    labels: tuple[str, ...]
    work_class: str
    mutation_class: str
    lane: str
    readiness: str = "ready"

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_number": self.issue_number,
            "repo": self.repo,
            "labels": list(self.labels),
            "work_class": self.work_class,
            "mutation_class": self.mutation_class,
            "lane": self.lane,
            "readiness": self.readiness,
        }


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


def infer_lane(labels: Sequence[str]) -> str:
    lane_needles = sorted(
        LANE_LABEL_MAP.items(), key=lambda item: len(item[0]), reverse=True
    )
    for label in labels:
        normalized = str(label or "").strip().lower()
        for needle, lane in lane_needles:
            if needle in normalized:
                return lane
    return "unclassified"


def read_queue_comment(
    repo: str = DEFAULT_REPO,
    queue_issue: int = DEFAULT_QUEUE_ISSUE,
    *,
    gh_runner: GhRunner | None = None,
) -> Mapping[str, Any] | None:
    runner = gh_runner or default_gh_runner
    code, payload, _stderr = _gh_api(
        runner,
        f"repos/{repo}/issues/{queue_issue}/comments?per_page=100",
        method="GET",
    )
    if code != 0 or not isinstance(payload, list):
        return None
    matches = [
        comment
        for comment in payload
        if isinstance(comment, Mapping) and QUEUE_SENTINEL in str(comment.get("body") or "")
    ]
    if not matches:
        return None
    return matches[-1]


def parse_queue_entries(body: str | None) -> tuple[QueueEntry, ...]:
    if not body:
        return ()
    entries: list[QueueEntry] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("| ---"):
            continue
        cells = _split_markdown_row(stripped)
        if len(cells) != 9 or cells[0].strip().lower() == "issue":
            continue
        try:
            issue_text = cells[0].strip()
            if issue_text.startswith("#"):
                issue_text = issue_text[1:]
            issue_number = int(issue_text)
            repo = _md_unescape(cells[1]).strip()
            title = _md_unescape(cells[2]).strip()
            work_class = cells[3].strip()
            mutation_class = cells[4].strip()
            lane = cells[5].strip()
            readiness = cells[6].strip()
            blockers = _parse_blockers(cells[7])
            triaged_at = cells[8].strip()
            if not repo or not triaged_at or readiness not in {"ready", "blocked"}:
                continue
            entries.append(
                QueueEntry(
                    issue_number=issue_number,
                    repo=repo,
                    title=title,
                    work_class=work_class,
                    mutation_class=mutation_class,
                    lane=lane,
                    readiness=readiness,
                    blockers=blockers,
                    triaged_at=triaged_at,
                )
            )
        except (TypeError, ValueError):
            continue
    return tuple(entries)


def render_queue_body(entries: Sequence[QueueEntry]) -> str:
    ordered = sorted(entries, key=lambda entry: (entry.issue_number, entry.repo.lower()))
    lines = [
        QUEUE_SENTINEL,
        "",
        NON_AUTHORITY_STATEMENT,
        "",
        "| Issue | Repo | Title | Work class | Mutation class | Lane | Readiness | Blockers | Triaged at |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in ordered:
        blockers = ", ".join(entry.blockers) if entry.blockers else "none"
        lines.append(
            "| "
            + " | ".join(
                [
                    f"#{entry.issue_number}",
                    _md_escape(entry.repo),
                    _md_escape(entry.title),
                    _md_escape(entry.work_class),
                    _md_escape(entry.mutation_class),
                    _md_escape(entry.lane),
                    _md_escape(entry.readiness),
                    _md_escape(blockers),
                    _md_escape(entry.triaged_at),
                ]
            )
            + " |"
        )
    return "\n".join(lines).rstrip() + "\n"


def classify_issue(
    raw: Any,
    *,
    default_repo: str | None = DEFAULT_REPO,
    triaged_at: str | None = None,
) -> QueueEntry | None:
    return plan_triage_entry(
        raw,
        default_repo=default_repo,
        triaged_at=triaged_at or utc_now_iso(),
    )


def plan_triage_entry(
    raw: Any,
    *,
    default_repo: str | None = DEFAULT_REPO,
    triaged_at: str,
) -> QueueEntry | None:
    candidate = forge_triage.normalize_issue(raw, default_repo=default_repo)
    if candidate is None:
        return None

    # Intentional private coupling: the ce-ops queue is a thin projection over
    # the forge triage classifier so P0 does not fork work/mutation inference.
    work_class = forge_triage._infer_work_class(candidate)
    mutation_class = forge_triage._infer_mutation_class(candidate)
    blockers = forge_triage.readiness_blockers(candidate)
    return QueueEntry(
        issue_number=candidate.number,
        repo=candidate.repo,
        title=candidate.title,
        work_class=work_class,
        mutation_class=mutation_class,
        lane=infer_lane(candidate.labels),
        readiness="blocked" if blockers else "ready",
        blockers=tuple(blockers),
        triaged_at=triaged_at,
    )


def pickup_candidates_from_issues(
    raw_issues: Sequence[Any],
    *,
    default_repo: str | None = DEFAULT_REPO,
    triaged_at: str,
) -> tuple[PickupCandidate, ...]:
    """Return advisory ready-to-dispatch candidates from raw triage inputs.

    This is a pure projection: it reuses the queue planner for classification
    and readiness, reads assignee/label/body state from normalized issues, and
    never performs GitHub I/O or mutations.

    Every candidate is also gated through ``forge_triage._skip_reason`` (with
    no ``gh_runner``) — the same pickup-safety predicate
    ``forge_triage.plan_triage`` uses before labeling an issue ready. That
    excludes the body-text form of the ``⏸ AWAITING-OPERATOR`` hold marker,
    aggregate/epic/tracker/rollup issues and work-class L, done-labeled
    issues, and issues whose ``state`` is not ``"open"``, in addition to the
    existing blocking-label/dependency and assignee/in-progress-label
    checks. Separately, this function also excludes any issue whose LABELS
    intersect ``AWAITING_OPERATOR_LABELS`` (``forge.controller_inbox``'s
    canonical hold-marker label set), so both the label form and the
    body-text form of the AWAITING-OPERATOR convention are excluded.

    IMPORTANT: because no ``gh_runner`` is supplied here, this does NOT run
    the live, network-dependent checks that ``_skip_reason`` performs when a
    ``gh_runner`` is available — in-flight/merged linked-PR status and active
    work-claim status. A ``readiness: "ready"`` candidate from this function
    is therefore advisory only; any consumer that actually dispatches a seat
    onto an issue MUST re-run the full ``forge_triage`` pickup gate (e.g.
    ``forge_triage.plan_triage``) with a live ``gh_runner`` first. See
    ``pickup_payload``'s ``requires_live_recheck`` field.
    """
    candidates: list[PickupCandidate] = []
    for raw in raw_issues:
        issue = forge_triage.normalize_issue(raw, default_repo=default_repo)
        if issue is None:
            continue
        entry = plan_triage_entry(raw, default_repo=default_repo, triaged_at=triaged_at)
        if entry is None:
            continue
        if entry.readiness != "ready" or entry.blockers:
            continue
        skip_reason = forge_triage._skip_reason(
            issue,
            arc_work_key=None,
            arc_held_refs={},
            gh_runner=None,
        )
        if skip_reason is not None:
            continue
        if _has_awaiting_operator_label(issue.labels):
            continue
        if issue.assignees or _has_pickup_in_progress_label(issue.labels):
            continue
        candidates.append(
            PickupCandidate(
                issue_number=entry.issue_number,
                repo=entry.repo,
                labels=tuple(sorted(issue.labels, key=str.lower)),
                work_class=entry.work_class,
                mutation_class=entry.mutation_class,
                lane=entry.lane,
            )
        )
    deduped = _dedupe_pickup_candidates(candidates)
    return tuple(sorted(deduped, key=_pickup_candidate_sort_key))


def pickup_payload(candidates: Sequence[PickupCandidate]) -> dict[str, Any]:
    return {
        "kind": "ce-triage-pickup-candidates",
        "schema_version": SCHEMA_VERSION,
        "advisory": NON_AUTHORITY_STATEMENT,
        "requires_live_recheck": True,
        "requires_live_recheck_note": (
            "readiness on each candidate here was computed without a live "
            "gh_runner (no in-flight/merged linked-PR or work-claim check). "
            "Any consumer that dispatches a seat onto a candidate MUST "
            "re-run the full forge_triage pickup gate "
            "(forge_triage.plan_triage / forge_triage._skip_reason) with a "
            "live gh_runner before dispatch."
        ),
        "candidate_count": len(candidates),
        "candidates": [candidate.to_dict() for candidate in candidates],
    }


def scan_and_triage(
    *,
    repo: str = DEFAULT_REPO,
    queue_issue: int = DEFAULT_QUEUE_ISSUE,
    audit_root: str | Path | None = None,
    apply: bool = False,
    gh_runner: GhRunner | None = None,
    updated_since_hours: int = DEFAULT_UPDATED_HOURS,
    now: str | None = None,
) -> dict[str, Any]:
    runner = gh_runner or default_gh_runner
    triaged_at = now or utc_now_iso()
    warnings: list[str] = []

    existing_comment = read_queue_comment(repo, queue_issue, gh_runner=runner)
    existing_entries = (
        parse_queue_entries(str(existing_comment.get("body") or ""))
        if existing_comment is not None
        else ()
    )
    if existing_comment is None:
        warnings.append("queue_comment_missing")

    raw_issues, issue_warning = _recent_issues(
        repo,
        updated_since_hours=updated_since_hours,
        now=triaged_at,
        gh_runner=runner,
    )
    if issue_warning:
        warnings.append(issue_warning)
    pickup_candidates = pickup_candidates_from_issues(
        raw_issues,
        default_repo=repo,
        triaged_at=triaged_at,
    )

    planned_entries: list[QueueEntry] = []
    label_plans: list[tuple[QueueEntry, Sequence[str]]] = []
    for raw in raw_issues:
        entry = plan_triage_entry(raw, default_repo=repo, triaged_at=triaged_at)
        if entry is None:
            continue
        planned_entries.append(entry)
        label_plans.append((entry, _current_issue_labels(raw, default_repo=repo)))
    label_result = sync_classification_labels(label_plans, apply=apply, gh_runner=runner)
    warnings.extend(str(warning) for warning in label_result.get("warnings", ()))
    merged = _dedupe_last_write([*existing_entries, *planned_entries])
    write_result = upsert_queue_comment(
        repo,
        queue_issue,
        merged,
        apply=apply,
        gh_runner=runner,
        existing_comment=existing_comment,
    )
    if write_result.get("warning"):
        warnings.append(str(write_result["warning"]))

    result: dict[str, Any] = {
        "kind": "ce-triage-queue-scan",
        "schema_version": SCHEMA_VERSION,
        "advisory": NON_AUTHORITY_STATEMENT,
        "repo": repo,
        "queue_issue": queue_issue,
        "applied": bool(apply and write_result.get("applied")),
        "scan_issue_count": len(raw_issues),
        "planned_entry_count": len(planned_entries),
        "queue_entry_count": len(merged),
        "entries": [entry.to_dict() for entry in merged],
        "pickup": pickup_payload(pickup_candidates),
        "write": write_result,
        "labels": label_result,
        "warnings": warnings,
    }
    audit_path = write_audit_record(audit_root, result, triaged_at=triaged_at)
    if audit_path is not None:
        result["audit_path"] = str(audit_path)
    return result


def plan_label_delta(entry: QueueEntry, current_labels: Sequence[str]) -> LabelDelta:
    desired = _desired_classification_labels(entry)
    current_managed = tuple(
        sorted(
            {
                label.strip()
                for label in current_labels
                if _is_managed_label(label.strip())
            }
        )
    )
    return LabelDelta(
        issue_number=entry.issue_number,
        repo=entry.repo,
        current_managed=current_managed,
        desired=desired,
        add=tuple(label for label in desired if label not in current_managed),
        remove=tuple(label for label in current_managed if label not in desired),
    )


def sync_classification_labels(
    issue_plans: Sequence[tuple[QueueEntry, Sequence[str]]],
    *,
    apply: bool = False,
    gh_runner: GhRunner | None = None,
) -> dict[str, Any]:
    runner = gh_runner or default_gh_runner
    deltas: list[LabelDelta] = []
    warnings: list[str] = []
    for entry, current_labels in issue_plans:
        delta = plan_label_delta(entry, current_labels)
        if apply and (delta.add or delta.remove):
            delta = _apply_label_delta(delta, gh_runner=runner)
            if delta.error:
                warnings.append(
                    f"label_apply_failed:{delta.repo}#{delta.issue_number}:{delta.error}"
                )
        deltas.append(delta)

    error_count = sum(1 for delta in deltas if delta.error)
    return {
        "applied": bool(apply),
        "planned": not apply,
        "managed_prefixes": list(MANAGED_LABEL_PREFIXES),
        "missing_label_policy": MISSING_LABEL_POLICY,
        "issue_count": len(deltas),
        "delta_count": sum(1 for delta in deltas if delta.add or delta.remove),
        "error_count": error_count,
        "deltas": [delta.to_dict() for delta in deltas],
        "warnings": warnings,
    }


def upsert_queue_comment(
    repo: str,
    queue_issue: int,
    entries: Sequence[QueueEntry],
    *,
    apply: bool = False,
    gh_runner: GhRunner | None = None,
    existing_comment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    runner = gh_runner or default_gh_runner
    comment = existing_comment
    if comment is None:
        comment = read_queue_comment(repo, queue_issue, gh_runner=runner)
    body = render_queue_body(entries)
    comment_id = _comment_id(comment)
    if comment_id is None:
        return {
            "applied": False,
            "planned": bool(not apply),
            "comment_id": None,
            "body_sha256": _sha256(body),
            "warning": "queue_comment_missing_no_create",
        }
    if not apply:
        return {
            "applied": False,
            "planned": True,
            "comment_id": comment_id,
            "body_sha256": _sha256(body),
        }
    code, _payload, stderr = _gh_api(
        runner,
        f"repos/{repo}/issues/comments/{comment_id}",
        method="PATCH",
        body={"body": body},
    )
    return {
        "applied": code == 0,
        "planned": False,
        "comment_id": comment_id,
        "body_sha256": _sha256(body),
        **({"warning": f"patch_failed:{stderr.strip() or code}"} if code != 0 else {}),
    }


def _apply_label_delta(delta: LabelDelta, *, gh_runner: GhRunner) -> LabelDelta:
    try:
        for label in delta.add:
            ok, detail = _ensure_label(delta.repo, label, gh_runner=gh_runner)
            if not ok:
                return _label_delta_error(delta, f"ensure_label_failed:{label}:{detail}")
        if delta.add:
            ok, detail = _add_issue_labels(
                delta.repo,
                delta.issue_number,
                delta.add,
                gh_runner=gh_runner,
            )
            if not ok:
                return _label_delta_error(delta, f"add_failed:{detail}")
        for label in delta.remove:
            ok, detail = _remove_issue_label(
                delta.repo,
                delta.issue_number,
                label,
                gh_runner=gh_runner,
            )
            if not ok:
                return _label_delta_error(delta, f"remove_failed:{label}:{detail}")
    except Exception as exc:  # noqa: BLE001 - advisory labels must fail open per issue.
        return _label_delta_error(delta, str(exc))
    return LabelDelta(
        issue_number=delta.issue_number,
        repo=delta.repo,
        current_managed=delta.current_managed,
        desired=delta.desired,
        add=delta.add,
        remove=delta.remove,
        applied=True,
    )


def _label_delta_error(delta: LabelDelta, error: str) -> LabelDelta:
    return LabelDelta(
        issue_number=delta.issue_number,
        repo=delta.repo,
        current_managed=delta.current_managed,
        desired=delta.desired,
        add=delta.add,
        remove=delta.remove,
        applied=False,
        error=error,
    )


def _desired_classification_labels(entry: QueueEntry) -> tuple[str, ...]:
    labels: list[str] = []
    work_label = f"wc:{entry.work_class}"
    if work_label in WORK_CLASS_LABELS:
        labels.append(work_label)
    readiness_label = f"triage:{entry.readiness}"
    if readiness_label in READINESS_LABELS:
        labels.append(readiness_label)
    return tuple(sorted(labels))


def _has_awaiting_operator_label(labels: Sequence[str]) -> bool:
    normalized = {forge_triage._label_key(label) for label in labels}
    return bool(normalized.intersection(AWAITING_OPERATOR_LABELS))


def _has_pickup_in_progress_label(labels: Sequence[str]) -> bool:
    normalized = {forge_triage._label_key(label) for label in labels}
    return bool(normalized.intersection(PICKUP_IN_PROGRESS_LABELS)) or any(
        label.startswith(PICKUP_IN_PROGRESS_LABEL_PREFIXES) for label in normalized
    )


def _pickup_candidate_sort_key(candidate: PickupCandidate) -> tuple[Any, ...]:
    return (
        _lane_sort_key(candidate.lane),
        _work_class_sort_key(candidate.work_class),
        candidate.issue_number,
        candidate.repo.lower(),
    )


def _lane_sort_key(lane: str) -> tuple[int, Any]:
    text = str(lane or "").strip().upper()
    if text.startswith("L") and text[1:].isdigit():
        return (0, int(text[1:]))
    return (1, text.lower())


def _work_class_sort_key(work_class: str) -> tuple[int, str]:
    order = {"XS": 0, "S": 1, "M": 2, "L": 3}
    text = str(work_class or "").strip().upper()
    return (order.get(text, 99), text)


def _is_managed_label(label: str) -> bool:
    return any(label.startswith(prefix) for prefix in MANAGED_LABEL_PREFIXES)


def _current_issue_labels(raw: Any, *, default_repo: str) -> tuple[str, ...]:
    candidate = forge_triage.normalize_issue(raw, default_repo=default_repo)
    return () if candidate is None else candidate.labels


def _ensure_label(repo: str, label: str, *, gh_runner: GhRunner) -> tuple[bool, str]:
    spec = LABEL_SPECS.get(label)
    if spec is None:
        return False, "missing_label_spec"
    path = f"repos/{repo}/labels/{_path_label(label)}"
    code, _payload, stderr = _gh_api(gh_runner, path, method="GET")
    if code == 0:
        return True, ""
    code, _payload, stderr = _gh_api(
        gh_runner,
        f"repos/{repo}/labels",
        method="POST",
        body={
            "name": label,
            "color": spec["color"],
            "description": spec["description"],
        },
    )
    return code == 0, stderr.strip() or str(code)


def _add_issue_labels(
    repo: str,
    issue_number: int,
    labels: Sequence[str],
    *,
    gh_runner: GhRunner,
) -> tuple[bool, str]:
    code, _payload, stderr = _gh_api(
        gh_runner,
        f"repos/{repo}/issues/{issue_number}/labels",
        method="POST",
        body={"labels": list(labels)},
    )
    return code == 0, stderr.strip() or str(code)


def _remove_issue_label(
    repo: str,
    issue_number: int,
    label: str,
    *,
    gh_runner: GhRunner,
) -> tuple[bool, str]:
    code, _payload, stderr = _gh_api(
        gh_runner,
        f"repos/{repo}/issues/{issue_number}/labels/{_path_label(label)}",
        method="DELETE",
    )
    return code == 0, stderr.strip() or str(code)


def _path_label(label: str) -> str:
    return urllib.parse.quote(label, safe="")


def write_audit_record(
    audit_root: str | Path | None,
    record: Mapping[str, Any],
    *,
    triaged_at: str | None = None,
) -> Path | None:
    if audit_root is None:
        return None
    root = Path(audit_root)
    root.mkdir(parents=True, exist_ok=True)
    stamp = _safe_stamp(triaged_at or utc_now_iso())
    path = root / f"ce-triage-queue-{stamp}.json"
    payload = dict(record)
    payload.setdefault("advisory", NON_AUTHORITY_STATEMENT)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def inspect_queue(
    *,
    repo: str = DEFAULT_REPO,
    queue_issue: int = DEFAULT_QUEUE_ISSUE,
    audit_root: str | Path | None = None,
    gh_runner: GhRunner | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    runner = gh_runner or default_gh_runner
    triaged_at = now or utc_now_iso()
    comment = read_queue_comment(repo, queue_issue, gh_runner=runner)
    entries = parse_queue_entries(str(comment.get("body") or "")) if comment else ()
    result: dict[str, Any] = {
        "kind": "ce-triage-queue-inspect",
        "schema_version": SCHEMA_VERSION,
        "advisory": NON_AUTHORITY_STATEMENT,
        "repo": repo,
        "queue_issue": queue_issue,
        "comment_id": _comment_id(comment),
        "queue_entry_count": len(entries),
        "entries": [entry.to_dict() for entry in entries],
        "warnings": [] if comment else ["queue_comment_missing"],
    }
    audit_path = write_audit_record(audit_root, result, triaged_at=triaged_at)
    if audit_path is not None:
        result["audit_path"] = str(audit_path)
    return result


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _recent_issues(
    repo: str,
    *,
    updated_since_hours: int,
    now: str,
    gh_runner: GhRunner,
) -> tuple[tuple[Any, ...], str | None]:
    since = _parse_utc(now) - timedelta(hours=max(updated_since_hours, 1))
    query = " ".join(
        [
            f"repo:{repo}",
            "is:issue",
            "is:open",
            f"updated:>={since.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        ]
    )
    path = "search/issues?" + urllib.parse.urlencode(
        {"q": query, "sort": "updated", "order": "asc", "per_page": "100"}
    )
    code, payload, stderr = _gh_api(gh_runner, path, method="GET")
    if code != 0 or not isinstance(payload, Mapping):
        return (), f"issue_scan_failed:{stderr.strip() or code}"
    items = payload.get("items")
    if not isinstance(items, list):
        return (), "issue_scan_malformed"
    return tuple(items), None


def _gh_api(
    runner: GhRunner,
    path: str,
    *,
    method: str | None = None,
    fields: Sequence[str] = (),
    body: Mapping[str, Any] | None = None,
) -> tuple[int, object, str]:
    argv: list[str] = ["gh", "api"]
    if method is not None:
        argv += ["--method", method]
    argv.append(path)
    for field in fields:
        argv += ["-f", field]
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


def _dedupe_last_write(entries: Sequence[QueueEntry]) -> tuple[QueueEntry, ...]:
    by_number: dict[int, QueueEntry] = {}
    for entry in entries:
        by_number[entry.issue_number] = entry
    return tuple(by_number[number] for number in sorted(by_number))


def _dedupe_pickup_candidates(
    candidates: Sequence[PickupCandidate],
) -> tuple[PickupCandidate, ...]:
    by_number: dict[int, PickupCandidate] = {}
    for candidate in candidates:
        by_number[candidate.issue_number] = candidate
    return tuple(by_number[number] for number in sorted(by_number))


def _comment_id(comment: Mapping[str, Any] | None) -> int | None:
    if not isinstance(comment, Mapping):
        return None
    try:
        return int(comment.get("id"))
    except (TypeError, ValueError):
        return None


def _parse_blockers(cell: str) -> tuple[str, ...]:
    value = _md_unescape(cell).strip()
    if not value or value == "none":
        return ()
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _md_escape(value: Any) -> str:
    text = str(value or "").replace("\\", "\\\\").replace("|", "\\|")
    return " ".join(text.splitlines()).strip()


def _md_unescape(value: str) -> str:
    out: list[str] = []
    escaped = False
    for char in value:
        if escaped:
            out.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        else:
            out.append(char)
    if escaped:
        out.append("\\")
    return "".join(out)


def _split_markdown_row(line: str) -> list[str]:
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in text:
        if escaped:
            current.append("\\")
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if escaped:
        current.append("\\")
    cells.append("".join(current).strip())
    return cells


def _parse_utc(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_stamp(value: str) -> str:
    return "".join(char if char.isalnum() else "-" for char in value).strip("-")


def _sha256(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()
