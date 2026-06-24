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
from collections.abc import Mapping, Sequence
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
    _PR_SEARCH_TYPE,
    _ORG_SCOPE_RE,
    _REPO_SCOPE_RE,
    _default_transport,
    _issue_number,
    _search_once,
)

DEFAULT_REVIEW_PICKUP_PER_PAGE = DEFAULT_SEARCH_PER_PAGE


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


def review_pickup_query(*, repo: str | None = None, org: str | None = None) -> SearchQuery:
    """Build the controller feed query for open PRs that may need review routing."""
    if repo and org:
        raise PickupError("--repo and --org are mutually exclusive search scopes")
    if not repo and not org:
        # Fail closed: an unscoped query builds `is:open is:pull-request` across every
        # open PR the token can see; with --apply that would request reviewers and
        # auto-dismiss stale reviews fleet-wide. Require exactly one explicit scope
        # (ce-ops#188 review, same fail-closed class as the ce-ops#218 queue-poll belt).
        raise PickupError(
            "review pickup refuses an unscoped query; supply repo or org "
            "(must not act across every PR a token can see)"
        )
    scope_terms: list[str] = []
    if repo:
        if not _REPO_SCOPE_RE.match(repo):
            raise PickupError(f"--repo must be owner/name, got {repo!r}")
        scope_terms.append(f"repo:{repo}")
    if org:
        if not _ORG_SCOPE_RE.match(org):
            raise PickupError(f"--org must be a GitHub organization/user slug, got {org!r}")
        scope_terms.append(f"org:{org}")
    return SearchQuery("awaiting_review", " ".join(["is:open", _PR_SEARCH_TYPE, *scope_terms]))


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
                apply=apply,
                apply_stale=apply_stale,
            )
        except (PickupError, ForgeConfigError) as exc:
            skipped.append({
                "repo": hit.get("repo"),
                "number": hit.get("number"),
                "reason": "review_pickup_refused",
                "note": str(exc),
            })
            continue
        if item is None:
            skipped.append({
                "repo": hit.get("repo"),
                "number": hit.get("number"),
                "reason": "review_not_awaiting_pickup",
            })
        else:
            items.append(item)

    return ReviewPickupResult(items=tuple(items), skipped=tuple(skipped), rate_limit=rate_limit or None)


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
    author = _login(pr.get("user"))
    head = pr.get("head") if isinstance(pr.get("head"), Mapping) else {}
    head_sha = str(head.get("sha") or "")
    if not author or not head_sha:
        raise PickupError(f"{repo}#{number} lacks author/head_sha; refusing fail-closed")

    requested = tuple(
        login for login in (
            _login(r) for r in pr.get("requested_reviewers", []) if isinstance(r, Mapping)
        )
        if login
    )
    non_author_requested = tuple(r for r in requested if r != author)

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
        )

    stale_reviewers = tuple(
        v.review.reviewer
        for v in report.re_request_needed
        if v.review.reviewer and v.review.reviewer != author
    )
    reviewer = _choose_reviewer(author=author, reviewer_seats=reviewer_seats, preferred=stale_reviewers)
    if reviewer is None:
        raise PickupError(f"{repo}#{number} has no distinct non-author reviewer candidate")

    reason = "stale_review_rerequest" if stale_reviewers else "awaiting_review"
    requested_now = False
    if apply:
        _request_pull_request_reviewer(repo, number, reviewer, gh_runner)
        requested_now = True

    return _review_pickup_item(
        hit,
        author=author,
        head_sha=head_sha,
        reviewer=reviewer,
        reason=reason,
        requested=requested_now,
        report=report,
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
) -> str | None:
    candidates = [*preferred, *_normalize_reviewer_seats(reviewer_seats)]
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate == author or candidate in seen:
            seen.add(candidate)
            continue
        return candidate
    return None


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
        "dismissed_review_ids": list(report.dismissed),
        "re_request_review_ids": [v.review.review_id for v in report.re_request_needed],
    }


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
