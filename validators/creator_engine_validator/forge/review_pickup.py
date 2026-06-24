"""Controller review-pickup leg (ce-ops#188) — the v3 review half of the belt.

Routes awaiting-review PRs to distinct **non-author** reviewer seats and handles
objectively stale reviews deterministically via :mod:`forge.re_review`. This is
the controller-side review leg that the per-seat work-poller (``pickup.py``, v1)
does not cover.

It is a **v3** module (it couples to the v3 forge: ``re_review`` +
``github_repo_config``). It shares the read-only GitHub Search primitives with
the v1 poller through the boundary-neutral ``pickup_search`` core, so no v1↔v3
import edge is created. All I/O is injectable (``transport`` for Search,
``gh_runner`` for PR/review reads+mutations); tests run entirely offline.
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from . import re_review
from .github_repo_config import ForgeConfigError
from ..pickup_search import (
    DEFAULT_SEARCH_PER_PAGE,
    GhRunner,
    PickupError,
    SearchQuery,
    Transport,
    build_scoped_search_query,
    declared_search_scope,
    _PR_SEARCH_TYPE,
    _default_transport,
    _issue_number,
    _search_once,
)

DEFAULT_REVIEW_PICKUP_PER_PAGE = DEFAULT_SEARCH_PER_PAGE
DEFAULT_REVIEW_PICKUP_INTERVAL_SECONDS = 300

LogSink = Callable[[Mapping[str, Any]], None]

_FAILED_CI_STATES = {
    "FAILURE",
    "ERROR",
    "FAILED",
    "failed",
    "failure",
    "error",
    "cancelled",
    "timed_out",
    "action_required",
}


@dataclass(frozen=True)
class ReviewPickupResult:
    """Controller-side review pickup result.

    ``items`` are the review work-items surfaced to the belt/controller. When
    ``apply=True`` they also record the reviewer request mutation outcome and
    stale-review reconciliation summary.
    """

    items: tuple[dict[str, Any], ...] = ()
    skipped: tuple[dict[str, Any], ...] = ()
    rate_limit: Mapping[str, Any] | None = None


class ReviewPickupSkip(Exception):
    """One PR was read successfully enough to skip with a bounded reason."""

    def __init__(self, reason: str, note: str | None = None) -> None:
        super().__init__(note or reason)
        self.reason = reason
        self.note = note


@dataclass(frozen=True)
class ReviewPickupLoopResult:
    passes: tuple[ReviewPickupResult, ...] = ()

    @property
    def item_count(self) -> int:
        return sum(len(result.items) for result in self.passes)

    @property
    def skipped_count(self) -> int:
        return sum(len(result.skipped) for result in self.passes)


def review_pickup_query(*, repo: str | None = None, org: str | None = None) -> SearchQuery:
    """Build the controller feed query for open PRs that may need review routing."""
    if not repo and not org:
        # Fail closed: an unscoped query builds `is:open is:pull-request` across every
        # open PR the token can see; with --apply that would request reviewers and
        # auto-dismiss stale reviews fleet-wide. Require exactly one explicit scope
        # (ce-ops#188 review, same fail-closed class as the ce-ops#218 queue-poll belt).
        raise PickupError(
            "review pickup refuses an unscoped query; supply repo or org "
            "(must not act across every PR a token can see)"
        )
    scope = declared_search_scope(repo=repo, org=org)
    return build_scoped_search_query("awaiting_review", ["is:open", _PR_SEARCH_TYPE], scope=scope)


def poll_review_pickup(
    *,
    token: str,
    reviewer_seats: Sequence[str],
    gh_runner: GhRunner,
    transport: Transport | None = None,
    repo: str | None = None,
    org: str | None = None,
    per_page: int = DEFAULT_REVIEW_PICKUP_PER_PAGE,
    apply: bool = False,
    apply_stale: bool = True,
    dry_run: bool = False,
    log_sink: LogSink | None = None,
) -> ReviewPickupResult:
    """Route awaiting-review PRs to distinct non-author reviewer seats.

    This is the controller-side review leg missing from the per-seat belt. It
    scans open PRs, reconciles objectively stale reviews through
    :mod:`forge.re_review`, and emits/optionally applies one non-author review
    request per PR that lacks a live non-author reviewer signal.

    All I/O is injectable: Search uses ``transport`` and PR/review mutations use
    ``gh_runner``. Tests run entirely offline.
    """
    if not token or not token.strip():
        raise PickupError("review pickup requires a non-empty token")
    seats = _normalize_reviewer_seats(reviewer_seats)
    if not seats:
        raise PickupError("review pickup requires at least one --seat reviewer")

    _transport = transport or _default_transport
    query = review_pickup_query(repo=repo, org=org)
    page_items, rate_limit = _search_once(
        token=token.strip(),
        transport=_transport,
        query=query,
        per_page=per_page,
    )

    effective_apply = bool(apply and not dry_run)
    reviewer_load: dict[str, int] = {seat: 0 for seat in seats}
    items: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for hit in page_items:
        if hit.get("subject_type") != "PullRequest":
            continue
        try:
            item = plan_review_pickup_item(
                hit,
                reviewer_seats=seats,
                gh_runner=gh_runner,
                apply=effective_apply,
                apply_stale=apply_stale,
                reviewer_load=reviewer_load,
                dry_run=dry_run,
            )
        except ReviewPickupSkip as exc:
            decision = {
                "repo": hit.get("repo"),
                "number": hit.get("number"),
                "reason": exc.reason,
                "note": exc.note,
                "dry_run": dry_run,
            }
            skipped.append(decision)
            _log_decision(log_sink, "skipped", decision)
            continue
        except (PickupError, ForgeConfigError) as exc:
            decision = {
                "repo": hit.get("repo"),
                "number": hit.get("number"),
                "reason": "review_pickup_refused",
                "note": str(exc),
                "dry_run": dry_run,
            }
            skipped.append(decision)
            _log_decision(log_sink, "skipped", decision)
            continue
        if item is None:
            decision = {
                "repo": hit.get("repo"),
                "number": hit.get("number"),
                "reason": "review_not_awaiting_pickup",
                "dry_run": dry_run,
            }
            skipped.append(decision)
            _log_decision(log_sink, "skipped", decision)
        else:
            items.append(item)
            _log_decision(log_sink, "routed", item)

    return ReviewPickupResult(items=tuple(items), skipped=tuple(skipped), rate_limit=rate_limit or None)


def run_review_pickup_loop(
    *,
    token: str,
    reviewer_seats: Sequence[str],
    gh_runner: GhRunner,
    transport: Transport | None = None,
    repo: str | None = None,
    org: str | None = None,
    per_page: int = DEFAULT_REVIEW_PICKUP_PER_PAGE,
    apply: bool = False,
    apply_stale: bool = True,
    dry_run: bool = False,
    iterations: int | None = 1,
    interval: float = DEFAULT_REVIEW_PICKUP_INTERVAL_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
    log_sink: LogSink | None = None,
) -> ReviewPickupLoopResult:
    """Run one or more bounded review-pickup passes.

    ``iterations=None`` is the daemon mode. Tests can pass a small integer and a
    no-op ``sleep`` to exercise loop behavior without an infinite process.
    """
    if iterations is not None and iterations < 1:
        raise PickupError("review pickup loop requires iterations >= 1")
    if iterations is None and interval <= 0:
        raise PickupError("review pickup loop requires interval > 0")
    passes: list[ReviewPickupResult] = []
    index = 0
    while iterations is None or index < iterations:
        index += 1
        _log_event(log_sink, "review_pickup_pass_start", index=index, dry_run=dry_run)
        result = poll_review_pickup(
            token=token,
            reviewer_seats=reviewer_seats,
            gh_runner=gh_runner,
            transport=transport,
            repo=repo,
            org=org,
            per_page=per_page,
            apply=apply,
            apply_stale=apply_stale,
            dry_run=dry_run,
            log_sink=log_sink,
        )
        passes.append(result)
        _log_event(
            log_sink,
            "review_pickup_pass_complete",
            index=index,
            routes=len(result.items),
            skipped=len(result.skipped),
            dry_run=dry_run,
        )
        if iterations is not None and index >= iterations:
            break
        sleep(interval)
    return ReviewPickupLoopResult(passes=tuple(passes))


def _normalize_reviewer_seats(seats: Sequence[str]) -> tuple[str, ...]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in seats or ():
        for part in str(raw).split(","):
            seat = part.strip()
            if seat and seat not in seen:
                seen.add(seat)
                out.append(seat)
    return tuple(out)


def plan_review_pickup_item(
    hit: Mapping[str, Any],
    *,
    reviewer_seats: Sequence[str],
    gh_runner: GhRunner,
    apply: bool = False,
    apply_stale: bool = True,
    reviewer_load: dict[str, int] | None = None,
    dry_run: bool = False,
) -> dict[str, Any] | None:
    """Plan/apply review routing for one PR Search hit.

    Returns ``None`` when the PR already has a live non-author reviewer signal
    (fresh approval, current non-author review request, or live CHANGES_REQUESTED
    on head). Otherwise returns a work-item-shaped routing record.
    """
    repo = str(hit.get("repo") or "")
    number = _issue_number(hit.get("number"))
    if not repo or number is None:
        raise PickupError("review pickup hit lacks repo/number")

    pr = _read_pull_request(repo, number, gh_runner)
    draft = pr.get("draft")
    if draft is True:
        raise ReviewPickupSkip("draft_pull_request", f"{repo}#{number} is a draft PR")
    if draft is not False:
        raise ReviewPickupSkip("draft_state_unknown", f"{repo}#{number} lacks draft=false; refusing fail-closed")

    author = _login(pr.get("user"))
    head = pr.get("head") if isinstance(pr.get("head"), Mapping) else {}
    head_sha = str(head.get("sha") or "")
    if not author or not head_sha:
        raise PickupError(f"{repo}#{number} lacks author/head_sha; refusing fail-closed")

    ci_state = _read_head_ci_state(repo, head_sha, gh_runner)
    ci_failures = _ci_failures(ci_state)
    if ci_failures:
        raise ReviewPickupSkip("ci_failed", f"{repo}#{number} head CI failed: {', '.join(ci_failures)}")

    requested = tuple(
        login for login in (
            _login(r) for r in pr.get("requested_reviewers", []) if isinstance(r, Mapping)
        )
        if login
    )
    non_author_requested = tuple(r for r in requested if r != author)
    if reviewer_load is not None:
        for reviewer in non_author_requested:
            reviewer_load[reviewer] = reviewer_load.get(reviewer, 0) + 1

    report = re_review.reconcile_reviews(
        repo,
        number,
        head_sha,
        gh_runner=gh_runner,
        apply=bool(apply and apply_stale),
    )

    if _has_current_non_author_approval(report, author):
        return None
    if _has_current_non_author_objection(report, author):
        return None
    if non_author_requested:
        return _review_pickup_item(
            hit,
            author=author,
            head_sha=head_sha,
            reviewer=non_author_requested[0],
            reason="review_already_requested",
            requested=False,
            report=report,
            dry_run=dry_run,
        )

    governed_seats = set(_normalize_reviewer_seats(reviewer_seats))
    # Stale reviews can influence reviewer preference, but autonomous daemon
    # routing must stay inside the explicitly supplied governed seat set.
    stale_reviewers = tuple(
        v.review.reviewer
        for v in report.re_request_needed
        if v.review.reviewer and v.review.reviewer != author and v.review.reviewer in governed_seats
    )
    reviewer = _choose_reviewer(
        author=author,
        reviewer_seats=reviewer_seats,
        preferred=stale_reviewers,
        reviewer_load=reviewer_load,
    )
    if reviewer is None:
        raise PickupError(f"{repo}#{number} has no distinct non-author reviewer candidate")

    reason = "stale_review_rerequest" if stale_reviewers else "awaiting_review"
    requested_now = False
    if apply:
        _request_pull_request_reviewer(repo, number, reviewer, gh_runner)
        requested_now = True
    if reviewer_load is not None:
        reviewer_load[reviewer] = reviewer_load.get(reviewer, 0) + 1

    return _review_pickup_item(
        hit,
        author=author,
        head_sha=head_sha,
        reviewer=reviewer,
        reason=reason,
        requested=requested_now,
        report=report,
        dry_run=dry_run,
    )


def _login(user: object) -> str | None:
    if not isinstance(user, Mapping):
        return None
    login = user.get("login")
    return login if isinstance(login, str) and login else None


def _choose_reviewer(
    *,
    author: str,
    reviewer_seats: Sequence[str],
    preferred: Sequence[str] = (),
    reviewer_load: Mapping[str, int] | None = None,
) -> str | None:
    candidates = [*preferred, *_normalize_reviewer_seats(reviewer_seats)]
    seen: set[str] = set()
    eligible: list[str] = []
    for candidate in candidates:
        if not candidate or candidate == author or candidate in seen:
            seen.add(candidate)
            continue
        seen.add(candidate)
        eligible.append(candidate)
    if not eligible:
        return None
    load = reviewer_load or {}
    indexed = tuple(enumerate(eligible))
    _, reviewer = min(indexed, key=lambda pair: (int(load.get(pair[1], 0)), pair[0]))
    return reviewer


def _has_current_non_author_approval(report: re_review.ReconcileReport, author: str) -> bool:
    return any(
        v.verdict == re_review.CURRENT
        and v.review.state.upper() == "APPROVED"
        and v.review.reviewer != author
        for v in report.verdicts
    )


def _has_current_non_author_objection(report: re_review.ReconcileReport, author: str) -> bool:
    return any(
        v.verdict == re_review.CURRENT
        and v.review.state.upper() == "CHANGES_REQUESTED"
        and v.review.reviewer != author
        for v in report.verdicts
    )


def _review_pickup_item(
    hit: Mapping[str, Any],
    *,
    author: str,
    head_sha: str,
    reviewer: str,
    reason: str,
    requested: bool,
    report: re_review.ReconcileReport,
    dry_run: bool = False,
) -> dict[str, Any]:
    repo = str(hit.get("repo") or "")
    number = int(hit.get("number") or 0)
    return {
        "repo": repo,
        "kind": "review_request",
        "number": number,
        "url": hit.get("url") or f"https://github.com/{repo}/pull/{number}",
        "reason": reason,
        "thread_id": f"review-pickup:{repo}:review_request:{number}:{head_sha[:12]}",
        "title": hit.get("title"),
        "subject_type": "PullRequest",
        "author": author,
        "assigned_reviewer": reviewer,
        "head_sha": head_sha,
        "requested": requested,
        "dry_run": dry_run,
        "dismissed_review_ids": list(report.dismissed),
        "re_request_review_ids": [v.review.review_id for v in report.re_request_needed],
    }


def _read_head_ci_state(repo: str, head_sha: str, gh_runner: GhRunner) -> Mapping[str, Any]:
    try:
        combined = _pickup_gh_json(gh_runner, "GET", f"repos/{repo}/commits/{head_sha}/status")
        checks = _pickup_gh_json(gh_runner, "GET", f"repos/{repo}/commits/{head_sha}/check-runs?per_page=100")
    except PickupError as exc:
        raise ReviewPickupSkip("ci_unreadable", str(exc)) from exc
    if not isinstance(combined, Mapping):
        raise ReviewPickupSkip("ci_unreadable", f"{repo}@{head_sha[:12]} combined status was not an object")
    if not isinstance(checks, Mapping):
        raise ReviewPickupSkip("ci_unreadable", f"{repo}@{head_sha[:12]} check-runs body was not an object")
    return {"combined": combined, "checks": checks}


def _ci_failures(ci_state: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    combined = ci_state.get("combined")
    checks = ci_state.get("checks")
    if not isinstance(combined, Mapping) or not isinstance(checks, Mapping):
        raise ReviewPickupSkip("ci_unreadable", "CI payload was incomplete")

    state = combined.get("state")
    if not isinstance(state, str) or not state:
        raise ReviewPickupSkip("ci_unreadable", "combined status payload is missing state")
    if _ci_value_failed(state):
        failures.append(f"combined:{state}")

    statuses = combined.get("statuses", [])
    if statuses is None:
        statuses = []
    if not isinstance(statuses, list):
        raise ReviewPickupSkip("ci_unreadable", "combined status payload has non-list statuses")
    for status in statuses:
        if not isinstance(status, Mapping):
            raise ReviewPickupSkip("ci_unreadable", "combined status entry was not an object")
        context = str(status.get("context") or "status")
        value = status.get("state")
        if isinstance(value, str) and _ci_value_failed(value):
            failures.append(f"{context}:{value}")

    check_runs = checks.get("check_runs")
    if not isinstance(check_runs, list):
        raise ReviewPickupSkip("ci_unreadable", "check-runs payload is missing check_runs")
    for run in check_runs:
        if not isinstance(run, Mapping):
            raise ReviewPickupSkip("ci_unreadable", "check-run entry was not an object")
        name = str(run.get("name") or "check")
        conclusion = run.get("conclusion")
        status = run.get("status")
        value = conclusion if isinstance(conclusion, str) and conclusion else status
        if isinstance(value, str) and _ci_value_failed(value):
            failures.append(f"{name}:{value}")
    return failures


def _ci_value_failed(value: str) -> bool:
    return (
        value in _FAILED_CI_STATES
        or value.lower() in _FAILED_CI_STATES
        or value.upper() in _FAILED_CI_STATES
    )


def _log_decision(log_sink: LogSink | None, outcome: str, decision: Mapping[str, Any]) -> None:
    _log_event(
        log_sink,
        "review_pickup_decision",
        outcome=outcome,
        repo=decision.get("repo"),
        number=decision.get("number"),
        reason=decision.get("reason"),
        assigned_reviewer=decision.get("assigned_reviewer"),
        requested=decision.get("requested"),
        dry_run=decision.get("dry_run"),
        note=decision.get("note"),
    )


def _log_event(log_sink: LogSink | None, event: str, **fields: Any) -> None:
    if log_sink is None:
        return
    payload = {"event": event, **{k: v for k, v in fields.items() if v is not None}}
    log_sink(payload)


class JsonLineLogger:
    """Simple JSONL witness logger for daemon/service use."""

    def __init__(self, stream) -> None:
        self.stream = stream

    def __call__(self, payload: Mapping[str, Any]) -> None:
        print(json.dumps(dict(payload), sort_keys=True), file=self.stream, flush=True)


def _pickup_gh_json(
    runner: GhRunner,
    method: str,
    path: str,
    body: Mapping[str, Any] | None = None,
) -> object:
    argv = ["gh", "api", "--method", method, path]
    input_text = None
    if body is not None:
        argv += ["--input", "-"]
        input_text = json.dumps(body)
    proc = runner(argv, input_text)
    if getattr(proc, "returncode", 1) != 0:
        raise PickupError(f"gh api {method} {path} failed: {(getattr(proc, 'stderr', '') or '').strip()[:200]}")
    out = (getattr(proc, "stdout", "") or "").strip()
    if not out:
        raise PickupError(f"gh api {method} {path} returned empty stdout")
    try:
        return json.loads(out)
    except json.JSONDecodeError as exc:
        raise PickupError(f"gh api {method} {path} returned non-JSON stdout") from exc


def _read_pull_request(repo: str, number: int, gh_runner: GhRunner) -> Mapping[str, Any]:
    raw = _pickup_gh_json(gh_runner, "GET", f"repos/{repo}/pulls/{number}")
    if not isinstance(raw, Mapping):
        raise PickupError(f"GET repos/{repo}/pulls/{number} returned non-object body")
    return raw


def _request_pull_request_reviewer(repo: str, number: int, reviewer: str, gh_runner: GhRunner) -> None:
    _pickup_gh_json(
        gh_runner,
        "POST",
        f"repos/{repo}/pulls/{number}/requested_reviewers",
        {"reviewers": [reviewer]},
    )
