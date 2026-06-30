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

    planned_entries = [
        entry
        for raw in raw_issues
        if (entry := plan_triage_entry(raw, default_repo=repo, triaged_at=triaged_at))
        is not None
    ]
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
        "write": write_result,
        "warnings": warnings,
    }
    audit_path = write_audit_record(audit_root, result, triaged_at=triaged_at)
    if audit_path is not None:
        result["audit_path"] = str(audit_path)
    return result


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
